from typing import List, Optional, Any, Dict
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
    # Convenience list of location names to visit (used by workflows and summary)
    locations_to_visit: List[str] = []
    # Raw full output from Location Agent (keeps the original parsed JSON)
    location_recommendations: Optional[Dict[str, Any]] = None

    # From Activity Agent
    # Keep the existing convenience list (per-day plans) and also raw output
    activities: Optional[List] = None
    activity_recommendations: Optional[Dict[str, Any]] = None

    # From Packing Agent
    packing_list: Optional[PackingOutput] = None

    # From Summary Agent
    summary: Optional[str] = None

    # Internal state
    retry_count: int = 0
