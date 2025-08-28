from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class UserMessage(BaseModel):
    user_id: str = Field(..., description = 'Unique user/Session id')
    text: str

class Slots(BaseModel):
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    preferences: Optional[str] = None
    # add budget slot and create a budget agent

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
    activity_json: Optional[ActivitiesOut] = None
    packing_json: Optional[PackingOut] = None
    clarifying_questions: Optional[List[str]] = None
    notes: Optional[str] = None

class FinalResponse(BaseModel):
    # user_id: str
    # final_response: str
    # agent_trace: AgentTrace
    # metadata: Optional[Dict] = None
    text: str
    trace: AgentTrace
