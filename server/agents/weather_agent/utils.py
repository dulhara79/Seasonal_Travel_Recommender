# weather_agent/utils.py

def format_forecast(forecast):
    return f"{forecast.date}: {forecast.weather}, {forecast.temperature}°C"

