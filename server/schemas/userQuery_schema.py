from pydantic import BaseModel
from typing import Optional

class UserQuerySchema(BaseModel):
    query: str
    additional_info: Optional[str] = None
    # user_id: str
    # session_id: str
    # timestamp: str  # ISO 8601 format
    # metadata: dict = None  # Optional additional information
