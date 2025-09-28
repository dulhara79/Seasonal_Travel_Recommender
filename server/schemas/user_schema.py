from pydantic import BaseModel, EmailStr
from datetime import datetime

# Request schema for user registration
class UserCreate(BaseModel):
    username: str
    name: str
    email: EmailStr
    password: str

# Response schema (what we send back to client)
class UserOut(BaseModel):
    id: str
    username: str
    name: str
    email: EmailStr
    created_at: datetime

# Schema for JWT token response
class Token(BaseModel):
    access_token: str
    token_type: str
