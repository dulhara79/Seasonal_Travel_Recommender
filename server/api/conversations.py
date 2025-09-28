from fastapi import APIRouter, Depends, HTTPException, status
from server.api.auth import get_current_user
from server.schemas.chat_schema import ConversationCreate, AppendMessagePayload
from server.utils.chat_history import create_conversation, append_message, get_conversation, list_conversations_for_user, delete_conversation
from typing import List

router = APIRouter(tags=["conversations"]) 


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_conv(payload: ConversationCreate, current_user=Depends(get_current_user)) -> dict:
    # Infer user id from the authenticated token instead of relying on client
    # supplied value (prevents spoofing and accidental mismatches).
    user_id = current_user.get("id")
    created = await create_conversation(user_id, payload.session_id, payload.title)
    print(f"API: conversation created for user={user_id} id={created.get('id') if created else None}")
    return created


@router.post("/append", status_code=status.HTTP_200_OK)
async def append(payload: AppendMessagePayload, current_user=Depends(get_current_user)) -> dict:
    # Verify conversation exists and belongs to user
    conv = await get_conversation(payload.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")

    ok = await append_message(payload.conversation_id, payload.message.role, payload.message.text, payload.message.metadata)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to append message")
    return {"ok": True}


@router.get("/{conversation_id}")
async def get_conv(conversation_id: str, current_user=Depends(get_current_user)) -> dict:
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    # Return conversation (raw) - conversion to Pydantic model left to client
    return conv


@router.get("/", response_model=List[dict])
async def list_convs(current_user=Depends(get_current_user)) -> List[dict]:
    user_id = current_user.get("id")
    convs = await list_conversations_for_user(user_id)
    return convs


@router.delete("/{conversation_id}")
async def delete_conv(conversation_id: str, current_user=Depends(get_current_user)) -> dict:
    conv = await get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("user_id") != current_user.get("id"):
        raise HTTPException(status_code=403, detail="Not allowed")
    ok = await delete_conversation(conversation_id)
    return {"deleted": ok}
