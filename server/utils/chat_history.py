from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from server.utils.db import get_db
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
import io

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
            created["id"] = str(created["_id"])
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
    if text is None:
        text = ""

    if len(text) > MAX_INLINE_MESSAGE_CHARS:
        try:
            bucket = AsyncIOMotorGridFSBucket(db)
            # upload_from_stream accepts filename and a file-like object
            gfs_id = await bucket.upload_from_stream(None, io.BytesIO(text.encode("utf-8")))
            full_text_gfs_id = str(gfs_id)
            preview_text = text[:TRUNCATE_PREVIEW_CHARS] + "... [truncated]"
            metadata["full_text_gfs_id"] = full_text_gfs_id
            metadata["truncated"] = True
        except Exception:
            # If upload fails for any reason, fall back to truncation only
            preview_text = text[:TRUNCATE_PREVIEW_CHARS] + "... [truncated]"
            metadata["truncated"] = True

    msg = {"role": role, "text": preview_text, "metadata": metadata, "timestamp": datetime.utcnow()}

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
