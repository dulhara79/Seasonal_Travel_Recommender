import os
import json
from dotenv import load_dotenv
from google import genai

from server.utils.config import GEMINI_API_KEY

# ----------------------
# Load environment variables
# ----------------------
# load_dotenv()
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in your .env file.")

client = genai.Client(api_key=GEMINI_API_KEY)

# ----------------------
# Helper: safely parse Gemini JSON output
# ----------------------
def safe_parse_locations(text, prev_response=None):
    # Remove markdown or backticks
    cleaned_text = text.strip().replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(cleaned_text)
        if "recommended_locations" not in data:
            data["recommended_locations"] = []
        data["status"] = "complete" if data["recommended_locations"] else "awaiting_location"
        return data
    except json.JSONDecodeError:
        # fallback to previous response or empty
        return {
            "recommended_locations": prev_response.get("recommended_locations", []) if prev_response else [],
            "status": "awaiting_location",
            "messages": []
        }

# ----------------------
# Main agent function
# ----------------------
def run_location_agent(state, prev_response=None):
    prompt = f"""
You are a travel assistant. Based on the user's trip request, recommend specific places to visit.
Return a JSON object with a single key "recommended_locations", which is a list of objects.
Each object must have:
- "name": Name of the place
- "type": Type of location (e.g., cultural, hiking/nature, scenic, adventure)
- "reason": Why this place is recommended for the user

Do NOT include extra explanations outside JSON.

User trip details:
Destination: {state.destination}
Start date: {state.start_date}
End date: {state.end_date}
Number of travelers: {state.no_of_traveler}
Budget: {state.budget}
Preferences: {', '.join(state.user_preferences), []}
Type of trip: {state.type_of_trip}

Example output:
{{
  "recommended_locations": [
    {{
      "name": "Knuckles Mountain Range",
      "type": "hiking/nature",
      "reason": "Perfect for hiking and nature photography with scenic trails and peaks."
    }},
    {{
      "name": "Temple of the Tooth (Sri Dalada Maligawa)",
      "type": "cultural",
      "reason": "Historic temple and cultural landmark in Kandy."
    }}
  ]
}}
"""

    # Call Gemini API
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    # Extract text and parse
    text_output = response.text
    parsed = safe_parse_locations(text_output, prev_response)
    return parsed

# # ----------------------
# # Example usage
# # ----------------------
# if __name__ == "__main__":
#     # Example trip input
#     state = {
#         "destination": "jaffna, Sri Lanka",
#         "start_date": "2025-12-10",
#         "end_date": "2025-12-17",
#         "no_of_traveler": 2,
#         "budget": "medium",
#         "user_preferences": ["hiking", "cultural sites", "nature photography"],
#         "type_of_trip": "adventure"
#     }
#
#     output = run_location_agent(state)
#     print(json.dumps(output, indent=2))
