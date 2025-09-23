from typing import Optional, List, Any

from pydantic import BaseModel

class SummaryAgentInputSchema(BaseModel):
    destination: str = None
    season: str = None
    start_date: str = None
    end_date: str = None
    no_of_traveler: int = None
    budget: str = None
    user_preferences: list[str] = []
    type_of_trip: str = None
    locations_to_visit: list[str] = []
    activities: Optional[List] = []
    packing_list: list[str] = []
    additional_info: Optional[Any] = None
    status: Optional[str] = None
    messages: list[dict] = []

class SummaryAgentOutputSchema(BaseModel):
    summary: str = None
    status: str = None
    messages: list[dict] = []
    