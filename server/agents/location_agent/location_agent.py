# # location_agent.py
# # """
# # ==================================================
# #  Location Agent - Seasonal Travel Recommender System
# # ==================================================
#
# # System Architecture:
# # --------------------
# # - User → Recommender System → Agents
# #     * Location Agent (this script)
# #     * Activity Agent
# #     * Packaging Agent
# #
# # - Data Flow: User input → Agents process → Final ranked recommendations
# # - Scalability: Microservice-based, can scale independently
# # - Responsible AI: Ensures fairness, transparency, and anonymization of user data
#
# # Agent Roles & Communication:
# # ----------------------------
# # - Location Agent: Suggests travel spots based on location, budget, and preferences
# # - Weather Agent: Filters based on climate/forecast
# # - Seasonal Agent: Considers events/festivals
# # - Recommender Core: Integrates all results for final suggestion
# # - Communication Protocol: JSON-based responses (API friendly)
#
# # Commercialization Notes:
# # ------------------------
# # - Target Users: Tourists, travel agencies, seasonal travelers
# # - Pricing Model:
# #     * Free tier → basic recommendations
# #     * Premium tier → personalized itineraries, seasonal event packages
# # - Revenue: Partnerships with hotels, airlines, tour operators
# # """
#
# import os
# import json
# from dotenv import load_dotenv
# from google import genai
#
#
# # Import schemas
# from server.schemas.location_agent_schemas import LocationAgentInputSchema, LocationAgentOutputSchema
#
#
# # ----------------------
# # Load environment variables
# # ----------------------
# load_dotenv()
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
#
# if not GEMINI_API_KEY:
#     raise ValueError("GEMINI_API_KEY is not set in your .env file.")
#
# client = genai.Client(api_key=GEMINI_API_KEY)
#
# # ----------------------
# # Helper: safely parse Gemini JSON output
# # ----------------------
# def safe_parse_locations(text, prev_response=None):
#     cleaned_text = text.strip().replace("```json", "").replace("```", "").strip()
#
#     try:
#         data = json.loads(cleaned_text)
#         if "recommended_locations" not in data:
#             data["recommended_locations"] = []
#         data["status"] = "complete" if data["recommended_locations"] else "awaiting_location"
#
#         # Responsible AI: Add fairness disclaimer
#         data["disclaimer"] = "Recommendations are generated fairly and do not store personal user data."
#         return data
#     except json.JSONDecodeError:
#         return {
#             "recommended_locations": prev_response.get("recommended_locations", []) if prev_response else [],
#             "status": "awaiting_location",
#             "messages": [],
#             "disclaimer": "Recommendations are generated fairly and do not store personal user data."
#         }
#
# # ----------------------
# # Main agent function
# # ----------------------
# def run_location_agent(state, prev_response=None):
#     """
#     Core function of the Location Agent.
#     Accepts user travel details, queries Gemini, and returns structured recommendations.
#     """
#
#     prompt = f"""
# You are a travel assistant. Based on the user's trip request, recommend specific places to visit.
# Return a JSON object with a single key "recommended_locations", which is a list of objects.
# Each object must have:
# - "name": Name of the place
# - "type": Type of location (e.g., cultural, hiking/nature, scenic, adventure)
# - "reason": Why this place is recommended for the user during the specific travel dates.
#             Mention typical weather, seasonal suitability, and any local events if relevant.
# Do NOT include explanations outside JSON.
#
# User trip details:
#
# Destination: {state.get('destination')}
# Start date: {state.get('start_date')}
# End date: {state.get('end_date')}
# Number of travelers: {state.get('no_of_traveler')}
# Budget: {state.get('budget')}
# Preferences: {', '.join(state.get('user_preferences', []))}
# Type of trip: {state.get('type_of_trip')}
#
# Make sure the reason explicitly refers to why the place is suitable for these dates.
# """
#
#     # Log communication flow
#     print("[Comm Flow] User → LocationAgent → RecommenderCore → User")
#
#     response = client.models.generate_content(
#         model="gemini-2.5-flash",
#         contents=prompt
#     )
#
#     text_output = response.text
#     parsed = safe_parse_locations(text_output, prev_response)
#     return parsed
#
#
# # ----------------------
# # Example demo (Progress Evidence)
# # ----------------------
# if __name__ == "__main__":
#     state = {
#         "destination": "Galle",
#         "start_date": "2025-12-10",
#         "end_date": "2025-12-17",
#         "no_of_traveler": 2,
#         "budget": "medium",
#         "user_preferences": ["hiking", "cultural sites", "nature photography"],
#         "type_of_trip": "adventure"
#     }
#
#     output = run_location_agent(state)
#     print("\n[Progress Demo Output]")
#     print(json.dumps(output, indent=2))
#
#     # Responsible AI reminder
#     print("\nNote: All recommendations are anonymized and consider fairness & accessibility.")
#

# python
# server/agents/location_agent/location_agent.py

import os
import json
from typing import Any, Optional
from dotenv import load_dotenv
from google import genai
import bleach

from server.schemas.location_agent_schemas import LocationAgentInputSchema, LocationAgentOutputSchema

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in your .env file.")

client = genai.Client(api_key=GEMINI_API_KEY)


def _get_field(state: Any, name: str, default: Any = "") -> Any:
    """
    Safely retrieve a field from a dict-like or attribute-like state object.
    """
    if state is None:
        return default
    if isinstance(state, dict):
        return state.get(name, default)
    return getattr(state, name, default)


def sanitize_text(val: Any) -> str:
    """
    Coerce value to text and sanitize with bleach.
    - dict/list -> JSON string
    - None -> empty string
    - other types -> str(...)
    """
    if val is None:
        text = ""
    elif isinstance(val, (dict, list)):
        try:
            text = json.dumps(val, ensure_ascii=False)
        except Exception:
            text = str(val)
    else:
        text = str(val)
    return bleach.clean(text, strip=True)


def safe_parse_locations(text: str, prev_response: Optional[dict] = None) -> dict:
    cleaned_text = (text or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned_text)
        if "recommended_locations" not in data:
            data["recommended_locations"] = []
        data["status"] = "complete" if data["recommended_locations"] else "awaiting_location"
        data["disclaimer"] = "Recommendations are generated fairly and do not store personal user data."
        return data
    except json.JSONDecodeError:
        return {
            "recommended_locations": prev_response.get("recommended_locations", []) if prev_response else [],
            "status": "awaiting_location",
            "messages": [],
            "disclaimer": "Recommendations are generated fairly and do not store personal user data."
        }


def run_location_agent(state: Any, prev_response: Optional[dict] = None) -> dict:
    """
    Core Location Agent: accepts `state` (dict or model), builds a safe prompt,
    queries Gemini, and returns parsed recommendations.
    """
    destination = sanitize_text(_get_field(state, "destination", ""))
    start_date = sanitize_text(_get_field(state, "start_date", ""))
    end_date = sanitize_text(_get_field(state, "end_date", ""))
    no_of_traveler = _get_field(state, "no_of_traveler", "")
    budget = sanitize_text(_get_field(state, "budget", ""))
    user_prefs = _get_field(state, "user_preferences", []) or []
    if isinstance(user_prefs, (list, tuple)):
        user_prefs_str = sanitize_text(", ".join(map(str, user_prefs)))
    else:
        user_prefs_str = sanitize_text(user_prefs)
    trip_type = sanitize_text(_get_field(state, "type_of_trip", ""))

    prompt = f"""
You are a travel assistant. Based on the user's trip request, recommend specific places to visit.
Return ONLY a valid JSON object with a single key \"recommended_locations\", which is a list of objects.
Each object must have:
 - \"name\": Name of the place (string)
 - \"type\": Type of location (e.g., cultural, hiking/nature, scenic, adventure) (string)
 - \"reason\": Why this place is recommended for the user during the specific travel dates,
            mentioning typical weather, seasonal suitability, and any local events if relevant (string)

Do NOT include any narrative outside the JSON. Respond strictly with JSON.

User trip details:
Destination: {destination}
Start date: {start_date}
End date: {end_date}
Number of travelers: {no_of_traveler}
Budget: {budget}
Preferences: {user_prefs_str}
Type of trip: {trip_type}
"""

    print("[Comm Flow] User → LocationAgent → Gemini")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text_output = getattr(response, "text", None) or json.dumps(response.__dict__, default=str)
    except Exception as exc:
        print(f"[LocationAgent] Gemini request failed: {exc}")
        return safe_parse_locations("", prev_response)

    parsed = safe_parse_locations(text_output, prev_response)

    print(f"DEBUG: [LocationAgent] Parsed response: {parsed}")
    return parsed


if __name__ == "__main__":
    demo_state = {
        "destination": "Galle",
        "start_date": "2025-12-10",
        "end_date": "2025-12-17",
        "no_of_traveler": 2,
        "budget": "medium",
        "user_preferences": ["hiking", "cultural sites", "nature photography"],
        "type_of_trip": "adventure"
    }

    output = run_location_agent(demo_state)
    print("\n[Progress Demo Output]")
    print(json.dumps(output, indent=2))
    print("\nNote: All recommendations are anonymized and consider fairness & accessibility.")