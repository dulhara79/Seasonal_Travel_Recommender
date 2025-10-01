from fastapi import APIRouter, Depends, HTTPException, status
from server.api.auth import get_current_user
from server.schemas.chat_schema import ConversationCreate, AppendMessagePayload
from server.utils.chat_history import create_conversation, append_message, get_conversation, \
    list_conversations_for_user, delete_conversation
from typing import List, Dict, Any # Added Dict, Any for the helper function
from bson.objectid import ObjectId # <--- NEW: Import ObjectId for type checking

router = APIRouter(tags=["conversations"])

# --- NEW HELPER FUNCTION ---
def convert_doc_to_json_serializable(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Converts MongoDB's ObjectId to string 'id' for JSON serialization."""
    if doc and doc.get("_id") and isinstance(doc["_id"], ObjectId):
        # Pop the ObjectId and add it back as a string 'id' field
        doc["id"] = str(doc.pop("_id"))
    return doc
# ---------------------------

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_conv(payload: ConversationCreate, current_user=Depends(get_current_user)) -> dict:
    """
    Creates a new conversation.
    """
    user_id = current_user.get("id")
    # create_conversation returns a dict where _id has been popped and 'id' string added.
    created = await create_conversation(user_id, payload.session_id, payload.title)
    if not created:
        raise HTTPException(status_code=500, detail="Failed to create conversation in database")

    # Ensure the newly created document is also cleaned up, in case create_conversation
    # did not handle the '_id' to 'id' conversion properly.
    return convert_doc_to_json_serializable(created)


@router.post("/append", status_code=status.HTTP_200_OK)
async def append(payload: AppendMessagePayload, current_user=Depends(get_current_user)) -> dict:
    """
    Appends a message to an existing conversation.
    """
    # Verify conversation exists and belongs to user
    conv = await get_conversation(payload.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")

    ok = await append_message(payload.conversation_id, payload.message.role, payload.message.text,
                              payload.message.metadata)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to append message")
    return {"ok": True}


# Lists all conversations
@router.get("/list", response_model=List[dict])
async def list_convs(current_user=Depends(get_current_user)) -> List[dict]:
    """Lists all conversations for the authenticated user."""
    user_id = current_user.get("id")
    convs = await list_conversations_for_user(user_id)
    # <--- CRITICAL FIX APPLIED HERE:
    # Convert all documents to be JSON serializable (ObjectId -> str 'id')
    return [convert_doc_to_json_serializable(conv) for conv in convs]


# Retrieves a single conversation by ID
@router.get("/{conversation_id}")
async def get_conv(conversation_id: str, current_user=Depends(get_current_user)) -> dict:
    """Retrieves a single conversation by its ID."""
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    # Apply conversion here as well, in case get_conversation returns raw document
    return convert_doc_to_json_serializable(conv)


@router.delete("/{conversation_id}")
async def delete_conv(conversation_id: str, current_user=Depends(get_current_user)) -> dict:
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    ok = await delete_conversation(conversation_id)
    return {"deleted": ok}
