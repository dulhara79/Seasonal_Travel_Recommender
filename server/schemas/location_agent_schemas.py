from pydantic import BaseModel
from typing import Optional, List

class LocationAgentInputSchema(BaseModel):
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    user_preferences: List[str] = []
    type_of_trip: Optional[str] = None
    no_of_traveler: Optional[int] = 1
    budget: Optional[str] = "medium"

class LocationAgentOutputSchema(BaseModel):
    locations: List[str] = []
    status: Optional[str] = "awaiting_location"
    messages: List[dict] = []
