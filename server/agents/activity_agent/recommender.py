# Core logic: builds prompt, calls Azure LLM, parses output

# Build prompt, send request to Azure LLM, parse JSON result.

def build_prompt(destination, dates, weather, preference):
    return f"""
    Suggest 3-5 activities for a traveler visiting {destination} from {dates[0]} to {dates[1]}.
    Weather forecast: {weather}.
    User preference: {preference}.
    Provide a JSON list of activities with explanations.
    """

# def parse_activity_suggestions(response):
#     try:
#         activities = json.loads(response)
#         return activities
#     except json.JSONDecodeError:
#         return {"error": "Failed to parse activity suggestions."}

