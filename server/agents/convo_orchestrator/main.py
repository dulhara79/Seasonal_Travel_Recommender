# import os
# from typing import Dict
# from fastapi import FastAPI, Depends, Header
# from fastapi.middleware.cors import CORSMiddleware
# from dotenv import load_dotenv
# from .schemas import UserMessage, FinalResponse, AgentTrace
# from .security import sanitize_input#, basic_auth_check
# from .nlp import extract_slots, build_clarifying_question, missing_slots
# from .orchestrator import (
#     call_weather_agent, call_activity_agent, call_packing_agent,
#     fallback_weather, fallback_activities, fallback_packing
# )
# from .utils import pretty_date, join_nonempty
# from .llm import polish_response
#
# load_dotenv()
#
# app = FastAPI(title="Seasonal Travel – Conversation & Orchestrator Agent", version="1.0.0")
#
# # CORS
# origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# if origins:
#     app.add_middleware(
#         CORSMiddleware,
#         allow_origins=origins,
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )
#
# # simple memory (per user_id) for slot filling across turns
# SESSION: Dict[str, dict] = {}
#
# def _get_env_auth():
#     return os.getenv("ADMIN_USERNAME", "admin"), os.getenv("ADMIN_PASSWORD", "admin123")
#
# def _ensure_session(uid: str):
#     if uid not in SESSION:
#         SESSION[uid] = {"slots": None}
#     return SESSION[uid]
#
# @app.post("/chat", response_model=FinalResponse)
# async def chat(
#     payload: UserMessage,
#     x_username: str | None = Header(default=None),
#     x_password: str | None = Header(default=None),
# ):
#     # Basic auth check (optional; comment out if public)
#     # basic_auth_check(x_username, x_password, *_get_env_auth())
#
#     text = sanitize_input(payload.text)
#     state = _ensure_session(payload.user_id)
#
#     # 1) NLP Extraction and slot merge
#     new_slots = extract_slots(text)
#     if state.get("slots"):
#         # merge: fill missing from previous
#         old = state["slots"]
#         new_slots.destination = new_slots.destination or old.destination
#         new_slots.start_date  = new_slots.start_date  or old.start_date
#         new_slots.end_date    = new_slots.end_date    or old.end_date
#         new_slots.preferences = new_slots.preferences or old.preferences
#     state["slots"] = new_slots
#
#     # 2) Clarify if missing critical slots
#     cq = build_clarifying_question(new_slots)
#     if cq:
#         draft = f"Got it. I still need a bit more info: {cq}"
#         trace = AgentTrace(nlp_json=new_slots, clarifying_question=cq, notes="Awaiting required slots.")
#         return FinalResponse(text=draft, trace=trace)
#
#     # 3) Call downstream agents (with graceful fallbacks)
#     weather = await call_weather_agent(new_slots)
#     if weather is None:
#         weather = fallback_weather(new_slots)
#
#     activities = await call_activity_agent(new_slots, weather)
#     if activities is None:
#         activities = fallback_activities(new_slots, weather)
#
#     packing = await call_packing_agent(new_slots, weather, activities)
#     if packing is None:
#         packing = fallback_packing(new_slots, weather, activities)
#
#     # 4) Compose final draft
#     dest = new_slots.destination
#     dates_str = join_nonempty([
#         pretty_date(new_slots.start_date),
#         pretty_date(new_slots.end_date)
#     ])
#     wx_summary = f"The weather around {dest} from {dates_str} looks {weather.avg_temp or 'seasonally typical'}."
#     if weather.conditions:
#         cond_bits = []
#         for c in weather.conditions[:4]:
#             status = c.status or "—"
#             cond_bits.append(f"{c.date}: {status}")
#         wx_summary += " Conditions: " + "; ".join(cond_bits) + "."
#
#     acts_lines = []
#     for a in activities.activities[:6]:
#         reason = f" ({a.reason})" if a.reason else ""
#         acts_lines.append(f"- {a.day}: {a.activity}{reason}")
#     acts_text = "\n".join(acts_lines) if acts_lines else "- (No activities available)"
#
#     pack_lines = [f"- {item}" for item in packing.packing_list[:20]] or ["- (No items)"]
#     pack_text = "\n".join(pack_lines)
#
#     draft = f"""**Plan for {dest} ({dates_str})**
#
# **Weather**
# {wx_summary}
#
# **Suggested Activities**
# {acts_text}
#
# **Packing List**
# {pack_text}
#
# _Why these suggestions?_ Outdoor ideas appear on clearer days; rainy forecasts drive indoor cultural options. Packing adapts to temperature and rain risk, plus your preference: {new_slots.preferences}.
# """
#
#     # 5) Optional LLM polishing for nicer tone
#     polished = polish_response(
#         system_prompt=(
#             "You are a concise, helpful travel assistant. Keep formatting tidy, non-repetitive, and user-friendly."
#             " Do not invent data—preserve facts; you may rephrase for clarity."
#         ),
#         draft=draft
#     )
#     final_text = polished or draft
#
#     trace = AgentTrace(
#         nlp_json=new_slots,
#         weather_json=weather,
#         activities_json=activities,
#         packing_json=packing,
#         clarifying_question=None,
#         notes="OK"
#     )
#     return FinalResponse(text=final_text, trace=trace)
#
# # @app.post("/reset")
# # def reset(user_id: str,
# #           x_username: str | None = Header(default=None),
# #           x_password: str | None = Header(default=None)):
# #     basic_auth_check(x_username, x_password, *_get_env_auth())
# #     SESSION.pop(user_id, None)
# #     return {"ok": True}

# convo_orchestrator/main.py
import os
from fastapi import FastAPI, Depends, HTTPException
from .schemas import UserTextIn, OrchestratorResult
from .security import authorize
from .orchestrator import Orchestrator
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Conversation & Orchestrator Agent (Member 1)")

# CORS for a frontend on localhost:3000 during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orch = Orchestrator()

@app.post("/plan", response_model=OrchestratorResult)
async def plan_trip(payload: UserTextIn, auth: bool = Depends(authorize)):
    """
    Main endpoint:
    - Accepts `user_text` in free form.
    - Returns structured orchestration result and final_text.
    """
    try:
        result = await orch.process(payload.user_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
