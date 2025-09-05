from pydantic import BaseModel, Field
from typing import Optional, List

class ActivityAgentInput(BaseModel):
    destination: str
    season: Optional[str] = None
    start_date: Optional[str] = None # YYYY-MM-DD
    end_date: Optional[str] = None # YYYY-MM-DD
    preferences: List[str] = Field(default_factory=list)
    no_of_traveler: Optional[int] = None
    budget: Optional[str] = None # low | medium | high
    user_preferences: List[str] = Field(default_factory=list)
    type_of_trip: Optional[str] = None # solo, family, etc.
    suggest_locations: List[str] = Field(default_factory=list)
    additional_info: Optional[str] = None
    status: Optional[str] = None
    messages: List[dict] = Field(default_factory=list)


class TimeSlotSuggestion(BaseModel):
    time_of_day: str # morning | noon | evening | night
    title: str
    why: str
    source_hints: List[str] = Field(default_factory=list) # URLs or doc metadata


class DayPlan(BaseModel):
    date: str # YYYY-MM-DD
    suggestions: List[TimeSlotSuggestion]


class ActivityAgentOutput(BaseModel):
    destination: str
    season: Optional[str] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD
    preferences: List[str] = Field(default_factory=list)
    no_of_traveler: Optional[int] = None
    budget: Optional[str] = None  # low | medium | high
    user_preferences: List[str] = Field(default_factory=list)
    type_of_trip: Optional[str] = None  # solo, family, etc.
    suggest_locations: List[str] = Field(default_factory=list)
    additional_info: Optional[str] = None
    status: Optional[str] = None
    messages: List[dict] = Field(default_factory=list)
    overall_theme: Optional[str] = None
    day_plans: List[DayPlan]
    notes: Optional[str] = None
