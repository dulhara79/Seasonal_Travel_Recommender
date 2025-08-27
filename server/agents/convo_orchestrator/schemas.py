from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class UserMessage(BaseModel):
    user_id: str = Field(..., description = 'Unique user/Session id')
    text: str

