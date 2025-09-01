# from pydantic import BaseModel, Field
# from typing import List, Optional, Dict
#
# class UserMessage(BaseModel):
#     user_id: str = Field(..., description = 'Unique user/Session id')
#     text: str
#
# class Slots(BaseModel):
#     destination: Optional[str] = None
#     start_date: Optional[str] = None
#     end_date: Optional[str] = None
#     preferences: Optional[str] = None
#     # add budget slot and create a budget agent
#
# class WeatherDay(BaseModel):
#     date: str
#     status: str
#     min_temp: Optional[float] = None
#     max_temp: Optional[float] = None
#     precipitation_mm: Optional[float] = None
#
# class WeatherOut(BaseModel):
#     avg_temp: Optional[str] = None
#     conditions: List[WeatherDay] = []
#
# class ActivityItem(BaseModel):
#     day: str
#     activity: str
#     reason: Optional[str] = None
#
# class ActivitiesOut(BaseModel):
#     activities: List[ActivityItem] = []
#
# class PackingOut(BaseModel):
#     packing_list: List[str] = []
#
# class AgentTrace(BaseModel):
#     nlp_json: Slots
#     weather_json: Optional[WeatherOut] = None
#     activity_json: Optional[ActivitiesOut] = None
#     packing_json: Optional[PackingOut] = None
#     clarifying_questions: Optional[List[str]] = None
#     notes: Optional[str] = None
#
# class FinalResponse(BaseModel):
#     # user_id: str
#     # final_response: str
#     # agent_trace: AgentTrace
#     # metadata: Optional[Dict] = None
#     text: str
#     trace: AgentTrace

# convo_orchestrator/schemas.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class UserTextIn(BaseModel):
    user_text: str

class SlotOutput(BaseModel):
    destination: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    preferences: Optional[str]

class WeatherDay(BaseModel):
    date: str
    status: str
    avg_temp: Optional[str]

class WeatherOutput(BaseModel):
    avg_temp: Optional[str]
    conditions: List[WeatherDay]

class ActivityItem(BaseModel):
    day: str
    activity: str

class ActivityOutput(BaseModel):
    activities: List[ActivityItem]

class PackingOutput(BaseModel):
    packing_list: List[str]

class OrchestratorResult(BaseModel):
    slots: SlotOutput
    weather: WeatherOutput
    activities: ActivityOutput
    packing: PackingOutput
    final_text: str
    explanation: Optional[str]

