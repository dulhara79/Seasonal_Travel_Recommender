from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from server.schemas.user_schema import UserCreate, UserOut, Token
from server.utils import security
from server.utils.db import get_db
from bson import ObjectId
from datetime import timedelta
import pymongo
import traceback

router = APIRouter(tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# --- Register endpoint ---
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
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
            "created_at": __import__("datetime").datetime.utcnow()
        }

        result = await users.insert_one(doc)
        created = await users.find_one({"_id": result.inserted_id})

        # Build response dict and validate using Pydantic model so any
        # validation errors are raised here (and logged) instead of causing
        # a silent 500 in FastAPI's response handling.
        created_user = {
            "id": str(created["_id"]),
            "username": created["username"],
            "name": created["name"],
            "email": created["email"],
            "created_at": created["created_at"]
        }

        # Validate and return
        try:
            UserOut(**created_user)
        except Exception as e:
            # Log specific validation error and re-raise so we can see it in logs
            print("Registration response validation error:", type(e).__name__, str(e))
            raise

        return created_user

    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                          detail="User with given email or username already exists")
    except Exception:
        print("Registration error:\n", traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# --- Login endpoint ---
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    users = db.users
    login_value = form_data.username  # client may send email or username

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
        expires_delta=timedelta(minutes=int(__import__("os").environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    )
    return {"access_token": access_token, "token_type": "bearer"}


# --- Get current user ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    from jose import JWTError
    try:
        payload = security.decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    db = get_db()
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return {
        "id": str(user_doc["_id"]),
        "username": user_doc["username"],
        "name": user_doc["name"],
        "email": user_doc["email"],
        "created_at": user_doc["created_at"]
    }


@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
