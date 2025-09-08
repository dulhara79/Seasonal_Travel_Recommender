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

async def call_packing_agent(slots: Slots, weather: WeatherOut, activities: ActivitiesOut) -> Optional[PackingOut]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post("{PACKING_AGENT_URL", json={
            'destination': slots.destination,
            'start_date': slots.start_date,
            'end_date': slots.end_date,
             "weather": weather.dict() if weather else None,
            "activities": activities.dict() if activities else None
        })
        r.raise_for_status()
        return PackingOut(**r.json())
    except Exception as e:
        print(f"Error calling Packing Agent: {e}")
        return None

# ---- Fallbacks if services are down ----
def fallback_weather(slots: Slots) -> WeatherOut:
    # Basic seasonal guess based on destination keywords (very naive)
    avg = "Warm"
    conditions = []
    if slots.start_date and slots.end_date:
        conditions.append({"date": slots.start_date, "status": "Sunny"})
        conditions.append({"date": slots.end_date, "status": "Cloudy"})
    return WeatherOut(avg_temp=avg, conditions=conditions)

def fallback_activities(slots: Slots, weather: Optional[WeatherOut]) -> ActivitiesOut:
    acts = []
    pref = (slots.preferences or "").lower()
    def add(day, act, reason=None):
        acts.append({"day": day, "activity": act, "reason": reason})
    # Simple logic
    if weather and weather.conditions:
        for day in weather.conditions[:3]:
            stat = (day.status or "").lower()
            if "rain" in stat:
                if "cultur" in pref:
                    add(day["date"], "Museum or indoor cultural tour", "Rainy → indoor")
                else:
                    add(day["date"], "Indoor tea tasting tour", "Rainy → indoor")
            else:
                if "cultur" in pref:
                    add(day["date"], "Temple visit & heritage walk", "Sunny/Cloudy → outdoor cultural")
                elif "advent" in pref:
                    add(day["date"], "Hike nearby viewpoints", "Good weather → outdoor")
                else:
                    add(day["date"], "Botanical garden & city stroll", "Mild weather → light outdoor")
    else:
        add(slots.start_date or "Day 1", "City highlights walk", "No weather → default plan")
        add(slots.end_date or "Day 2", "Local market & food tour", "No weather → default plan")
    return ActivitiesOut(activities=acts)

def fallback_packing(slots: Slots, weather: Optional[WeatherOut], activities: Optional[ActivitiesOut]) -> PackingOut:
    pack = ["Passport/ID", "Phone + charger", "Reusable water bottle"]
    pref = (slots.preferences or "").lower()
    avg = (weather.avg_temp or "").lower() if weather else ""
    if "warm" in avg or not avg:
        pack += ["Light cotton clothes", "Sunscreen", "Hat", "Comfortable walking shoes"]
    if weather and any("rain" in (d.status or "").lower() for d in weather.conditions):
        pack += ["Umbrella or light raincoat"]
    if "cultur" in pref:
        pack += ["Modest attire for temple visits"]
    if "advent" in pref or "hike" in pref:
        pack += ["Hiking shoes", "Small daypack"]
    return PackingOut(packing_list=sorted(list(dict.fromkeys(pack))))
