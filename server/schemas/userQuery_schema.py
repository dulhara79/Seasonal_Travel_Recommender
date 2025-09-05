from pydantic import BaseModel

class UserQuerySchema(BaseModel):
    query: str
    # user_id: str
    # session_id: str
    # timestamp: str  # ISO 8601 format
    # metadata: dict = None  # Optional additional information
