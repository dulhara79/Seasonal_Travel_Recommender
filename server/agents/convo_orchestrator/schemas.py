from pydantic import BaseModel
from typing import List, Optional

class UserMessage(BaseModel):
    user_id: str
    text: str

class Slots(BaseModel):
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    preferences: Optional[str] = None

class WeatherDay(BaseModel):
    date: str
    status: str
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    precipitation_mm: Optional[float] = None

class WeatherOut(BaseModel):
    avg_temp: Optional[str] = None
    conditions: List[WeatherDay] = []

class ActivityItem(BaseModel):
    day: str
    activity: str
    reason: Optional[str] = None

class ActivitiesOut(BaseModel):
    activities: List[ActivityItem] = []

class PackingOut(BaseModel):
    packing_list: List[str] = []

class AgentTrace(BaseModel):
    nlp_json: Slots
    weather_json: Optional[WeatherOut] = None
    activities_json: Optional[ActivitiesOut] = None
    packing_json: Optional[PackingOut] = None
    clarifying_question: Optional[str] = None
    notes: Optional[str] = None

class FinalResponse(BaseModel):
    text: str
    trace: AgentTrace
