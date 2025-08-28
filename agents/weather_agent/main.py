from fastapi import FastAPI, HTTPException
from agents.weather_agent.api_client import get_weather_forecast
from agents.weather_agent.schemas import WeatherRequest

app = FastAPI(
    title="Weather Agent",
    description="A simple FastAPI weather agent",
    version="1.0.0"
)

@app.post("/forecast")
def forecast(request: WeatherRequest):
    """
    Expects a JSON body like:
    {
        "destination": "Colombo",
        "start_date": "2025-08-29",
        "end_date": "2025-09-02"
    }
    """
    try:
        weather_data = get_weather_forecast(
            request.destination, request.start_date, request.end_date
        )
        return {
            "destination": request.destination,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "forecast": weather_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch forecast: {e}")
