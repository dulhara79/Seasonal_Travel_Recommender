# main.py
import os
from typing import Dict
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from schemas import UserMessage, FinalResponse, AgentTrace, Slots
from security import sanitize_input
from nlp import extract_slots, build_clarifying_question
from orchestrator import (
    call_weather_agent, call_activity_agent, call_packing_agent,
    fallback_weather, fallback_activities, fallback_packing
)
from utils import pretty_date, join_nonempty
from llm import polish_response

load_dotenv()

app = FastAPI(title="Seasonal Travel – Conversation & Orchestrator Agent", version="1.0.0")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

SESSION: Dict[str, dict] = {}

def _ensure_session(uid: str):
    if uid not in SESSION:
        SESSION[uid] = {"slots": None}
    return SESSION[uid]

@app.post("/chat", response_model=FinalResponse)
async def chat(
    payload: UserMessage,
    x_username: str | None = Header(default=None),
    x_password: str | None = Header(default=None),
):
    text = sanitize_input(payload.text)
    state = _ensure_session(payload.user_id)

    # NLP extraction
    new_slots = extract_slots(text)
    # merge with previous if present
    if state.get("slots"):
        old: Slots = state["slots"]
        # only fill missing fields
        merged = Slots(
            destination = new_slots.destination or old.destination,
            start_date = new_slots.start_date or old.start_date,
            end_date = new_slots.end_date or old.end_date,
            preferences = new_slots.preferences or old.preferences
        )
        new_slots = merged
    state["slots"] = new_slots

    # clarifying question if necessary
    cq = build_clarifying_question(new_slots)
    if cq:
        draft = f"Got it. I still need a bit more info: {cq}"
        trace = AgentTrace(nlp_json=new_slots, clarifying_question=cq, notes="Awaiting required slots.")
        return FinalResponse(text=draft, trace=trace)

    # downstream agents (graceful fallbacks)
    weather = await call_weather_agent(new_slots) or fallback_weather(new_slots)
    activities = await call_activity_agent(new_slots, weather) or fallback_activities(new_slots, weather)
    packing = await call_packing_agent(new_slots, weather, activities) or fallback_packing(new_slots, weather, activities)

    # compose
    dest = new_slots.destination or "your destination"
    dates_str = join_nonempty([pretty_date(new_slots.start_date), pretty_date(new_slots.end_date)])
    wx_summary = f"The weather around {dest} from {dates_str} looks {weather.avg_temp or 'seasonally typical'}."
    if getattr(weather, "conditions", None):
        cond_bits = []
        for c in weather.conditions[:4]:
            status = getattr(c, "status", "—")
            cond_bits.append(f"{c.date}: {status}")
        wx_summary += " Conditions: " + "; ".join(cond_bits) + "."

    acts_lines = []
    for a in getattr(activities, "activities", [])[:6]:
        reason = f" ({a.reason})" if getattr(a, "reason", None) else ""
        acts_lines.append(f"- {a.day}: {a.activity}{reason}")
    acts_text = "\n".join(acts_lines) if acts_lines else "- (No activities available)"

    pack_lines = [f"- {item}" for item in getattr(packing, "packing_list", [])[:20]] or ["- (No items)"]
    pack_text = "\n".join(pack_lines)

    draft = f"""**Plan for {dest} ({dates_str})**

**Weather**
{wx_summary}

**Suggested Activities**
{acts_text}

**Packing List**
{pack_text}

_Why these suggestions?_ Outdoor ideas appear on clearer days; rainy forecasts drive indoor cultural options. Packing adapts to temperature and rain risk, plus your preference: {new_slots.preferences or 'general'}.
"""

    polished = polish_response(
        system_prompt=(
            "You are a concise, helpful travel assistant. Keep formatting tidy, non-repetitive, and user-friendly. "
            "Do not invent data—preserve facts; you may rephrase for clarity."
        ),
        draft=draft
    )
    final_text = polished or draft

    trace = AgentTrace(
        nlp_json=new_slots,
        weather_json=weather,
        activities_json=activities,
        packing_json=packing,
        clarifying_question=None,
        notes="OK"
    )
    return FinalResponse(text=final_text, trace=trace)
