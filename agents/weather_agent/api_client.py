# weather_agent/api_client.py
import requests
from datetime import datetime
from .schemas import WeatherResponse, DailyForecast

API_KEY = "bdaaa8c8d1c87e006536868334eb3a63"
BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"

def get_weather_forecast(destination: str, start_date: str, end_date: str) -> WeatherResponse:
    params = {
        "q": destination,
        "appid": API_KEY,
        "units": "metric"
    }
    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    forecasts = []
    for item in data.get("list", []):
        forecast_date = item["dt_txt"].split(" ")[0]
        if start_date <= forecast_date <= end_date:
            forecasts.append(DailyForecast(
                date=forecast_date,
                temperature=item["main"]["temp"],
                weather=item["weather"][0]["description"]
            ))

    return WeatherResponse(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        forecasts=forecasts
    )
