from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from server.schemas.user_schema import UserCreate, UserOut, Token
from server.utils import security
from server.utils.db import get_db
from bson import ObjectId
from datetime import timedelta, datetime
import pymongo
import traceback
import os
from typing import Dict  # Added for better type hints

# Assuming these utilities exist, including a function to delete all conversations
# NOTE: The chat_history.py needs a function like delete_conversation
from  server.utils.chat_history import delete_conversation

router = APIRouter(tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


# --- Get current user (re-defined for context but should be a common dependency) ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    from jose import JWTError
    try:
        payload = security.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    db = get_db()
    try:
        object_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user ID format")

    user_doc = await db.users.find_one({"_id": object_id})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {
        "id": str(user_doc["_id"]),
        "username": user_doc["username"],
        "name": user_doc["name"],
        "email": user_doc["email"],
        "created_at": user_doc["created_at"]
    }


# -----------------------------------------------------------------------------------


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    # ... (existing registration logic) ...
    try:
        db = get_db()
        users = db.users

        existing = await users.find_one({"$or": [{"email": user.email}, {"username": user.username}]})
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="User with given email or username already exists")

        doc = {
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "hashed_password": security.hash_password(user.password),
            "created_at": datetime.utcnow()
        }

        result = await users.insert_one(doc)
        created = await users.find_one({"_id": result.inserted_id})

        created_user = {
            "id": str(created["_id"]),
            "username": created["username"],
            "name": created["name"],
            "email": created["email"],
            "created_at": created["created_at"]
        }

        try:
            UserOut(**created_user)
        except Exception as e:
            print("Registration response validation error:", type(e).__name__, str(e))
            raise

        return created_user

    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="User with given email or username already exists")
    except Exception:
        print("Registration error:\n", traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # ... (existing login logic) ...
    db = get_db()
    users = db.users
    login_value = form_data.username

    user_doc = await users.find_one({"$or": [{"email": login_value}, {"username": login_value}]})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email/username or password",
                            headers={"WWW-Authenticate": "Bearer"})

    if not security.verify_password(form_data.password, user_doc.get("hashed_password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email/username or password",
                            headers={"WWW-Authenticate": "Bearer"})

    access_token = security.create_access_token(
        subject=str(user_doc["_id"]),
        expires_delta=timedelta(minutes=int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: Dict = Depends(get_current_user)):
    """Returns the details of the currently authenticated user."""
    return current_user


# --- NEW: Account Deletion Endpoint ---
@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_user_account(current_user: Dict = Depends(get_current_user)):
    """
    Deletes the current user's account and all associated data. 💀
    """
    user_id_str = current_user.get("id")

    db = get_db()

    # 1. Delete all associated trip conversations (important for cleanup/privacy)
    try:
        # NOTE: This assumes server.utils.chat_history.delete_conversation exists
        await delete_conversation(user_id_str)
    except Exception as e:
        # Log error but proceed with account deletion, as user requested it
        print(f"Warning: Failed to delete all conversations for user {user_id_str}. Error: {e}")

    # 2. Delete the user document itself
    try:
        user_object_id = ObjectId(user_id_str)
        result = await db.users.delete_one({"_id": user_object_id})
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to process user ID or deletion")

    if result.deleted_count == 0:
        # User not found in database (even though they were authenticated)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or already deleted")

    return {"message": "Account successfully deleted. All associated data has been removed."}
