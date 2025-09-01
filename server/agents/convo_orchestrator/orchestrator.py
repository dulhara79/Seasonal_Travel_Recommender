# import os
# import httpx
# from typing import Optional
# from .schemas import Slots, WeatherOut, ActivitiesOut, PackingOut
#
# WEATHER_AGENT_URL = os.getenv('WEATHER_AGENT_URL')
# ACTIVITY_AGENT_URL = os.getenv("ACTIVITY_AGENT_URL")
# PACKING_AGENT_URL = os.getenv("PACKING_AGENT_URL")
#
# async def call_weather_agent(slots: Slots) -> Optional[WeatherOut]:
#     try:
#         async with httpx.AsyncClient(timeout=20.0) as client:
#             r = await client.post(f"{WEATHER_AGENT_URL}", json={
#                 'destination': slots.destination,
#                 'start_date': slots.start_date,
#                 'end_date': slots.end_date
#             })
#             r.raise_for_status()
#             return WeatherOut(**r.json())
#     except Exception as e:
#         print(f"Error calling Weather Agent: {e}")
#         return None
#
# async def call_activity_agent(slots: Slots, weather: WeatherOut) -> Optional[ActivitiesOut]:
#     try:
#         async with httpx.AsyncClient(timeout=20.0) as client:
#             r = await client.post(f"{ACTIVITY_AGENT_URL}", json={
#             'destination': slots.destination,
#             'start_date': slots.start_date,
#             'end_date': slots.end_date,
#             'weather': weather.weather_description
#             })
#             r.raise_for_status()
#             return ActivitiesOut(**r.json())
#     except Exception as e:
#         print(f"Error calling Activity Agent: {e}")
#         return None
#
# async def call_packing_agent(slots: Slots, weather: WeatherOut, activities: ActivitiesOut) -> Optional[PackingOut]:
#     try:
#         async with httpx.AsyncClient(timeout=20.0) as client:
#             r = await client.post("{PACKING_AGENT_URL", json={
#             'destination': slots.destination,
#             'start_date': slots.start_date,
#             'end_date': slots.end_date,
#              "weather": weather.dict() if weather else None,
#             "activities": activities.dict() if activities else None
#         })
#         r.raise_for_status()
#         return PackingOut(**r.json())
#     except Exception as e:
#         print(f"Error calling Packing Agent: {e}")
#         return None
#
# # ---- Fallbacks if services are down ----
# def fallback_weather(slots: Slots) -> WeatherOut:
#     # Basic seasonal guess based on destination keywords (very naive)
#     avg = "Warm"
#     conditions = []
#     if slots.start_date and slots.end_date:
#         conditions.append({"date": slots.start_date, "status": "Sunny"})
#         conditions.append({"date": slots.end_date, "status": "Cloudy"})
#     return WeatherOut(avg_temp=avg, conditions=conditions)
#
# def fallback_activities(slots: Slots, weather: Optional[WeatherOut]) -> ActivitiesOut:
#     acts = []
#     pref = (slots.preferences or "").lower()
#     def add(day, act, reason=None):
#         acts.append({"day": day, "activity": act, "reason": reason})
#     # Simple logic
#     if weather and weather.conditions:
#         for day in weather.conditions[:3]:
#             stat = (day.status or "").lower()
#             if "rain" in stat:
#                 if "cultur" in pref:
#                     add(day["date"], "Museum or indoor cultural tour", "Rainy → indoor")
#                 else:
#                     add(day["date"], "Indoor tea tasting tour", "Rainy → indoor")
#             else:
#                 if "cultur" in pref:
#                     add(day["date"], "Temple visit & heritage walk", "Sunny/Cloudy → outdoor cultural")
#                 elif "advent" in pref:
#                     add(day["date"], "Hike nearby viewpoints", "Good weather → outdoor")
#                 else:
#                     add(day["date"], "Botanical garden & city stroll", "Mild weather → light outdoor")
#     else:
#         add(slots.start_date or "Day 1", "City highlights walk", "No weather → default plan")
#         add(slots.end_date or "Day 2", "Local market & food tour", "No weather → default plan")
#     return ActivitiesOut(activities=acts)
#
# def fallback_packing(slots: Slots, weather: Optional[WeatherOut], activities: Optional[ActivitiesOut]) -> PackingOut:
#     pack = ["Passport/ID", "Phone + charger", "Reusable water bottle"]
#     pref = (slots.preferences or "").lower()
#     avg = (weather.avg_temp or "").lower() if weather else ""
#     if "warm" in avg or not avg:
#         pack += ["Light cotton clothes", "Sunscreen", "Hat", "Comfortable walking shoes"]
#     if weather and any("rain" in (d.status or "").lower() for d in weather.conditions):
#         pack += ["Umbrella or light raincoat"]
#     if "cultur" in pref:
#         pack += ["Modest attire for temple visits"]
#     if "advent" in pref or "hike" in pref:
#         pack += ["Hiking shoes", "Small daypack"]
#     return PackingOut(packing_list=sorted(list(dict.fromkeys(pack))))

import os
from .nlp import parse_user_text
from .schemas import SlotOutput, OrchestratorResult, WeatherOutput, ActivityOutput, PackingOutput
from .utils import post_json_with_retry
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
WEATHER_AGENT_URL = os.getenv("WEATHER_AGENT_URL")
ACTIVITY_AGENT_URL = os.getenv("ACTIVITY_AGENT_URL")
PACKING_AGENT_URL = os.getenv("PACKING_AGENT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(temperature=OPENAI_TEMPERATURE, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)

class Orchestrator:
    def __init__(self):
        self.weather_url = WEATHER_AGENT_URL
        self.activity_url = ACTIVITY_AGENT_URL
        self.packing_url = PACKING_AGENT_URL

    async def process(self, user_text: str) -> OrchestratorResult:
        # 1) Slot extraction
        slots: SlotOutput = parse_user_text(user_text)

        # 2) Call Weather Agent
        weather_payload = {
            "destination": slots.destination,
            "start_date": slots.start_date,
            "end_date": slots.end_date
        }
        if not self.weather_url:
            raise RuntimeError("WEATHER_AGENT_URL not configured")
        weather_resp = await post_json_with_retry(self.weather_url, weather_payload)

        # Expect weather_resp shaped like WeatherOutput
        weather = WeatherOutput(**weather_resp)

        # 3) Call Activity Agent
        activity_payload = {
            "destination": slots.destination,
            "dates": {"start": slots.start_date, "end": slots.end_date},
            "preferences": slots.preferences,
            "weather": weather_resp
        }
        activity_resp = await post_json_with_retry(self.activity_url, activity_payload)
        activities = ActivityOutput(**activity_resp)

        # 4) Call Packing Agent
        packing_payload = {
            "weather": weather_resp,
            "activities": activity_resp,
            "preferences": slots.preferences
        }
        packing_resp = await post_json_with_retry(self.packing_url, packing_payload)
        packing = PackingOutput(**packing_resp)

        # 5) LLM: Combine into a nice natural-language response
        final_text, explanation = self._generate_natural_text(slots, weather, activities, packing)

        return OrchestratorResult(
            slots=slots,
            weather=weather,
            activities=activities,
            packing=packing,
            final_text=final_text,
            explanation=explanation
        )

    def _generate_natural_text(self, slots, weather, activities, packing):
        system_prompt = (
            "You are a friendly travel assistant. Given structured JSON containing destination, dates, weather, "
            "activities and packing list, produce: 1) a short friendly recommendation paragraph (3-5 sentences) describing the weather, three suggested activities mapped to dates, and a concise packing bullet list, and 2) a one-paragraph explanation of *why* those suggestions were chosen (mention weather and user preference). "
            "Keep the language concise and actionable. Do not invent facts not in the JSON. If dates are missing, say so politely."
        )
        human_msg = (
            f"INPUT JSON:\n"
            f"destination: {slots.destination}\n"
            f"start_date: {slots.start_date}\n"
            f"end_date: {slots.end_date}\n"
            f"preferences: {slots.preferences}\n\n"
            f"weather: {weather.json()}\n"
            f"activities: {activities.json()}\n"
            f"packing: {packing.json()}\n\n"
            "Produce JSON with fields: final_text (string), explanation (string)."
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_msg)
        ]
        resp = llm(messages)
        # llm returns ChatResult; extract content
        content = resp.content if hasattr(resp, "content") else str(resp)
        # Try to parse content to separate final_text and explanation. We'll be permissive:
        # Very common output is plain text; we'll attempt to split by "Explanation:" or "WHY:"
        final_text, explanation = self._split_llm_response(content)
        return final_text, explanation

    @staticmethod
    def _split_llm_response(content: str):
        # Look for markers
        markers = ["Explanation:", "Why:", "WHY:", "Reason:"]
        for m in markers:
            if m in content:
                parts = content.split(m, 1)
                return parts[0].strip(), parts[1].strip()
        # fallback: first paragraph = final_text, rest = explanation
        paras = [p.strip() for p in content.split("\n\n") if p.strip()]
        if len(paras) == 1:
            return paras[0], ""
        return paras[0], " ".join(paras[1:])
