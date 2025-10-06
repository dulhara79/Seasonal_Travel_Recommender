from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

from server.utils.config import JWT_SECRET, JWT_ALGORITHM

# hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = JWT_SECRET
ALGORITHM = JWT_ALGORITHM

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(subject: str, expires_delta: timedelta):
    expire = datetime.utcnow() + expires_delta
    to_encode = {"exp": expire, "sub": subject}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
