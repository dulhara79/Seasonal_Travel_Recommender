import os
import httpx
from typing import Optional
from .schemas import Slots, WeatherOut, ActivitiesOut, PackingOut

WEATHER_AGENT_URL = os.getenv('WEATHER_AGENT_URL')
ACTIVITY_AGENT_URL = os.getenv("ACTIVITY_AGENT_URL")
PACKING_AGENT_URL = os.getenv("PACKING_AGENT_URL")

async def call_weather_agent(slots: Slots) -> Optional[WeatherOut]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(f"{WEATHER_AGENT_URL}", json={
                'destination': slots.destination,
                'start_date': slots.start_date,
                'end_date': slots.end_date
            })
            r.raise_for_status()
            return WeatherOut(**r.json())
    except Exception as e:
        print(f"Error calling Weather Agent: {e}")
        return None

async def call_activity_agent(slots: Slots, weather: WeatherOut) -> Optional[ActivitiesOut]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(f"{ACTIVITY_AGENT_URL}", json={
            'destination': slots.destination,
            'start_date': slots.start_date,
            'end_date': slots.end_date,
            'weather': weather.weather_description
            })
            r.raise_for_status()
            return ActivitiesOut(**r.json())
    except Exception as e:
        print(f"Error calling Activity Agent: {e}")
        return None

