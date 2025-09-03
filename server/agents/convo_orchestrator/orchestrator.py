# orchestrator.py
import os
import httpx
from typing import Any
from schemas import Slots, WeatherOut, ActivitiesOut, PackingOut

WEATHER_AGENT_URL = os.getenv('WEATHER_AGENT_URL')
ACTIVITY_AGENT_URL = os.getenv("ACTIVITY_AGENT_URL")
PACKING_AGENT_URL = os.getenv("PACKING_AGENT_URL")



async def call_weather_agent(slots: Slots) -> WeatherOut | None:
    # implement your call to weather microservice / model here
    # return None on failure
    return None

async def call_activity_agent(slots: Slots, weather: WeatherOut) -> ActivitiesOut | None:
    return None

async def call_packing_agent(slots: Slots, weather: WeatherOut, activities: ActivitiesOut) -> PackingOut | None:
    return None

def fallback_weather(slots: Slots) -> WeatherOut:
    # Very small sensible fallback
    return WeatherOut(avg_temp="seasonally typical", conditions=[])

def fallback_activities(slots: Slots, weather: WeatherOut) -> ActivitiesOut:
    return ActivitiesOut(activities=[])

def fallback_packing(slots: Slots, weather: WeatherOut, activities: ActivitiesOut) -> PackingOut:
    return PackingOut(packing_list=["Basic clothing", "Toiletries"])
