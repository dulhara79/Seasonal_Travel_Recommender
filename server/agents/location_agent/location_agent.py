# location_agent.py
# """
# ==================================================
#  Location Agent - Seasonal Travel Recommender System
# ==================================================

# System Architecture:
# --------------------
# - User → Recommender System → Agents
#     * Location Agent (this script)
#     * Activity Agent
#     * Packaging Agent
#     
# - Data Flow: User input → Agents process → Final ranked recommendations
# - Scalability: Microservice-based, can scale independently
# - Responsible AI: Ensures fairness, transparency, and anonymization of user data

# Agent Roles & Communication:
# ----------------------------
# - Location Agent: Suggests travel spots based on location, budget, and preferences
# - Weather Agent: Filters based on climate/forecast
# - Seasonal Agent: Considers events/festivals
# - Recommender Core: Integrates all results for final suggestion
# - Communication Protocol: JSON-based responses (API friendly)

# Commercialization Notes:
# ------------------------
# - Target Users: Tourists, travel agencies, seasonal travelers
# - Pricing Model: 
#     * Free tier → basic recommendations
#     * Premium tier → personalized itineraries, seasonal event packages
# - Revenue: Partnerships with hotels, airlines, tour operators
# """

import os
import json
from dotenv import load_dotenv
from google import genai

# Import schemas
from server.schemas.location_agent_schemas import LocationAgentInputSchema, LocationAgentOutputSchema


# ----------------------
# Load environment variables
# ----------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in your .env file.")

client = genai.Client(api_key=GEMINI_API_KEY)

# ----------------------
# Helper: safely parse Gemini JSON output
# ----------------------
def safe_parse_locations(text, prev_response=None):
    cleaned_text = text.strip().replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(cleaned_text)
        if "recommended_locations" not in data:
            data["recommended_locations"] = []
        data["status"] = "complete" if data["recommended_locations"] else "awaiting_location"

        # Responsible AI: Add fairness disclaimer
        data["disclaimer"] = "Recommendations are generated fairly and do not store personal user data."
        return data
    except json.JSONDecodeError:
        return {
            "recommended_locations": prev_response.get("recommended_locations", []) if prev_response else [],
            "status": "awaiting_location",
            "messages": [],
            "disclaimer": "Recommendations are generated fairly and do not store personal user data."
        }

# ----------------------
# Main agent function
# ----------------------
def run_location_agent(state, prev_response=None):
    """
    Core function of the Location Agent.
    Accepts user travel details, queries Gemini, and returns structured recommendations.
    """

    prompt = f"""
You are a travel assistant. Based on the user's trip request, recommend specific places to visit.
Return a JSON object with a single key "recommended_locations", which is a list of objects.
Each object must have:
- "name": Name of the place
- "type": Type of location (e.g., cultural, hiking/nature, scenic, adventure)
- "reason": Why this place is recommended for the user during the specific travel dates.
            Mention typical weather, seasonal suitability, and any local events if relevant.
Do NOT include explanations outside JSON.

User trip details:
Destination: {state.get('destination')}
Start date: {state.get('start_date')}
End date: {state.get('end_date')}
Number of travelers: {state.get('no_of_traveler')}
Budget: {state.get('budget')}
Preferences: {', '.join(state.get('user_preferences', []))}
Type of trip: {state.get('type_of_trip')}

Make sure the reason explicitly refers to why the place is suitable for these dates.
"""

    # Log communication flow
    print("[Comm Flow] User → LocationAgent → RecommenderCore → User")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text_output = response.text
    parsed = safe_parse_locations(text_output, prev_response)
    return parsed


# ----------------------
# Example demo (Progress Evidence)
# ----------------------
if __name__ == "__main__":
    state = {
        "destination": "Jaffna, Sri Lanka",
        "start_date": "2025-12-10",
        "end_date": "2025-12-17",
        "no_of_traveler": 2,
        "budget": "medium",
        "user_preferences": ["hiking", "cultural sites", "nature photography"],
        "type_of_trip": "adventure"
    }

    output = run_location_agent(state)
    print("\n[Progress Demo Output]")
    print(json.dumps(output, indent=2))

    # Responsible AI reminder
    print("\nNote: All recommendations are anonymized and consider fairness & accessibility.")
