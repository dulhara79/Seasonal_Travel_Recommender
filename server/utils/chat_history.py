from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from server.utils.db import get_db
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
import io
from server.utils.config import ENCRYPTION_KEY
from base64 import urlsafe_b64encode, urlsafe_b64decode

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception:
    Fernet = None
    InvalidToken = Exception
import hashlib

# Configuration: max inline chars allowed per message. Messages larger than
# this will have a truncated preview stored inline while the full text is
# uploaded to GridFS and referenced by the message metadata.
MAX_INLINE_MESSAGE_CHARS = 5000
TRUNCATE_PREVIEW_CHARS = 5000


async def create_conversation(user_id: str, session_id: Optional[str] = None, title: Optional[str] = None) -> dict:
    db = get_db()
    doc = {
        "user_id": user_id,
        "session_id": session_id,
        "title": title,
        "messages": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    try:
        res = await db.conversations.insert_one(doc)
        inserted_id = res.inserted_id
        created = await db.conversations.find_one({"_id": inserted_id})
        # Convert ObjectId for convenience
        if created:
            # --- MANDATORY FIX: Ensure _id is converted to 'id' before returning ---
            created["id"] = str(created.pop("_id")) # Use pop to remove the ObjectId key
        print(f"create_conversation: inserted id={inserted_id}")
        return created
    except Exception as e:
        print("create_conversation error:", type(e).__name__, str(e))
        raise

async def append_message(conversation_id: str, role: str, text: str, metadata: dict | None = None) -> bool:
    db = get_db()
    metadata = metadata or {}

    # If message is too large to safely keep inline, upload to GridFS and
    # store a truncated preview inline with pointer to GridFS id.
    full_text_gfs_id = None
    preview_text = text
    # Compute SHA-256 hash of the message text and store in metadata. If text is large
    # and later uploaded to GridFS, hash the original full text before truncation/upload.
    try:
        if text is None:
            text_to_hash = ""
        else:
            text_to_hash = text
        sha256 = hashlib.sha256()
        sha256.update(text_to_hash.encode("utf-8"))
        metadata["text_hash"] = sha256.hexdigest()
        metadata["text_hash_algo"] = "sha256"
    except Exception:
        # If hashing fails for any reason, continue without blocking message storage
        pass

    # If encryption is available and a key is configured, encrypt the original
    # text and store ciphertext in metadata (or GridFS for large messages).
    encrypted_blob = None
    if ENCRYPTION_KEY and Fernet:
        try:
            f = Fernet(ENCRYPTION_KEY.encode())
            encrypted_blob = f.encrypt((text or "").encode("utf-8"))
            # store ciphertext inline for small messages; for large messages we'll
            # upload ciphertext to GridFS below (overwriting full_text_gfs_id).
            metadata["encrypted_text"] = urlsafe_b64encode(encrypted_blob).decode()
            metadata["encrypted"] = True
            metadata["encryption_algo"] = "fernet"
        except Exception:
            encrypted_blob = None
    if text is None:
        text = ""

    if len(text) > MAX_INLINE_MESSAGE_CHARS:
        try:
            bucket = AsyncIOMotorGridFSBucket(db)
            # upload_from_stream accepts filename and a file-like object
            # Upload the original full text or encrypted blob to GridFS. Prefer
            # to upload ciphertext if available to avoid storing plaintext.
            to_upload = encrypted_blob if encrypted_blob is not None else text.encode("utf-8")
            gfs_id = await bucket.upload_from_stream(None, io.BytesIO(to_upload))
            full_text_gfs_id = str(gfs_id)
            metadata["full_text_gfs_id"] = full_text_gfs_id
            metadata["truncated"] = True
            # If we uploaded ciphertext, remove inline copy to avoid duplication
            if encrypted_blob is not None and "encrypted_text" in metadata:
                metadata.pop("encrypted_text", None)
        except Exception:
            # If upload fails for any reason, fall back to truncation only
            preview_text = text[:TRUNCATE_PREVIEW_CHARS] + "... [truncated]"
            metadata["truncated"] = True

    # For privacy / compliance we avoid storing the full plaintext inline.
    # Store only the hash and any GridFS pointer or encrypted inline blob in metadata.
    msg = {"role": role, "text": "", "metadata": metadata, "timestamp": datetime.utcnow()}

    try:
        res = await db.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$push": {"messages": msg}, "$set": {"updated_at": datetime.utcnow()}}
        )
        print(f"append_message: conversation_id={conversation_id} modified={res.modified_count}")
        return res.modified_count == 1
    except Exception as e:
        print("append_message error:", type(e).__name__, str(e))
        raise


async def decrypt_message_text(message: dict) -> str | None:
    """Given a message dict (as stored), return the decrypted plaintext if available.

    - If message.metadata contains `encrypted_text`, decrypt and return it.
    - If metadata contains `full_text_gfs_id`, fetch from GridFS and decrypt if
      ciphertext was stored; otherwise return decoded plaintext bytes.
    - Returns None if decryption/fetching fails or no content available.
    """
    db = get_db()
    metadata = message.get("metadata", {}) or {}
    # Use inline encrypted_text if present
    try:
        if metadata.get("encrypted_text") and ENCRYPTION_KEY and Fernet:
            f = Fernet(ENCRYPTION_KEY.encode())
            ciphertext = urlsafe_b64decode(metadata["encrypted_text"].encode())
            return f.decrypt(ciphertext).decode("utf-8")
    except Exception:
        return None

    # Fallback: if full_text_gfs_id present, fetch and attempt to decrypt
    try:
        if metadata.get("full_text_gfs_id"):
            bucket = AsyncIOMotorGridFSBucket(db)
            from bson import ObjectId as BObject
            stream = await bucket.open_download_stream(BObject(metadata["full_text_gfs_id"]))
            data = await stream.read()
            # Try decrypting if encryption was used
            if metadata.get("encryption_algo") == "fernet" and ENCRYPTION_KEY and Fernet:
                f = Fernet(ENCRYPTION_KEY.encode())
                try:
                    return f.decrypt(data).decode("utf-8")
                except InvalidToken:
                    return None
            # Otherwise assume plaintext bytes
            return data.decode("utf-8")
    except Exception:
        return None


async def get_conversation(conversation_id: str) -> dict | None:
    db = get_db()
    doc = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
    if not doc:
        return None
    # Convert ObjectId to str for id
    doc["id"] = str(doc["_id"])
    return doc


async def list_conversations_for_user(user_id: str, limit: int = 20) -> List[dict]:
    db = get_db()
    cursor = db.conversations.find({"user_id": user_id}).sort("updated_at", -1).limit(limit)
    results = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        results.append(doc)
    return results


async def delete_conversation(conversation_id: str) -> bool:
    db = get_db()
    res = await db.conversations.delete_one({"_id": ObjectId(conversation_id)})
    return res.deleted_count == 1


async def update_conversation_title(conversation_id: str, title: str) -> dict | None:
    """Update conversation title and return updated document (with 'id' key)."""
    db = get_db()
    try:
        res = await db.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"title": title, "updated_at": datetime.utcnow()}}
        )
        if res.modified_count == 1:
            doc = await db.conversations.find_one({"_id": ObjectId(conversation_id)})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
        return None
    except Exception as e:
        print("update_conversation_title error:", type(e).__name__, str(e))
        raise
