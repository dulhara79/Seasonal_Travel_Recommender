from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Any, Dict
from .packing_agent import generate_packing_list

app = FastAPI(title="Packing Agent", version="1.0.0")


class ActivityAgentInput(BaseModel):
    location: str
    season: str
    start_date: str
    end_date: str
    preferences: List[str] = []
    no_of_traveler: int = 1
    budget: str = "medium"
    user_preferences: List[str] = []
    type_of_trip: str = "solo"
    suggest_locations: List[str] = []

class SuggestRequest(BaseModel):
    activity_input: ActivityAgentInput
    suggested_activities: List[str] = []

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/packing/suggest")
def suggest(req: SuggestRequest) -> Dict[str, Any]:
    # produce the packing list (LLM if key available, otherwise rules)
    return generate_packing_list(req.activity_input.model_dump(), req.suggested_activities, use_llm=True)
