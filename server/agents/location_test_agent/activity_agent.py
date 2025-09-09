# activity_agent.py

from google import genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=api_key)

def generate_activity_plan(attractions, location, start_date, end_date):
    if not attractions:
        return "No attractions to plan activities for."
    
    chat = client.chats.create(model="gemini-1.5-flash")  # valid model
    
    prompt = f"""
You are a travel activity planner.
User will visit {location} from {start_date} to {end_date}.
Recommend activities or an itinerary based on these attractions: {', '.join(attractions)}.
Make it friendly and easy to follow.
"""
    res = chat.send_message(prompt)
    return res.text
