from pydantic import BaseModel
from typing import Optional

class OrchestratorAgent4InputSchema(BaseModel):
    # user_id: Optional[str]
    query: Optional[str] = None

class OrchestratorAgent4OutpuSchema(BaseModel):
    location: Optional[str] = None
    season: Optional[str] = "Dry Season"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    user_preferences: list[str]= []
    no_of_traveler: Optional[int] = 1
    budget: Optional[str] = "medium"
    type_of_trip: Optional[str] = None
    additional_info: Optional[str] = None
    status: Optional[str] = None
    messages: list[dict] = []
