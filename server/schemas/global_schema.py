from typing import List, Optional, Any
from pydantic import BaseModel, Field

class PackingItem(BaseModel):
    name: str
    reason: Optional[str] = None


class PackingCategory(BaseModel):
    name: str
    items: List[PackingItem] = Field(default_factory=list)


class PackingOutput(BaseModel):
    summary: Optional[str] = None
    duration_days: Optional[int] = None
    categories: List[PackingCategory] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class TravelState(BaseModel):
    # From Orchestrator
    destination: Optional[str] = None
    season: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    no_of_traveler: Optional[int] = None
    budget: Optional[str] = None
    user_preferences: List[str] = []
    type_of_trip: Optional[str] = None
    additional_info: Optional[Any] = None
    status: Optional[str] = None
    messages: List[dict] = []

    # From Location Agent
    locations_to_visit: List[str] = []

    # From Activity Agent
    activities: Optional[List] = None

    # From Packing Agent
    packing: Optional[PackingOutput] = None

    # From Summary Agent
    summary: Optional[str] = None

    # Internal state
    retry_count: int = 0
