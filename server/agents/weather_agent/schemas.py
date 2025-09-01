# weather_agent/schemas.py
from pydantic import BaseModel
from typing import List

class WeatherRequest(BaseModel):
    destination: str
    start_date: str
    end_date: str

class DailyForecast(BaseModel):
    date: str
    temperature: float
    weather: str

class WeatherResponse(BaseModel):
    destination: str
    start_date: str
    end_date: str
    forecasts: List[DailyForecast]
