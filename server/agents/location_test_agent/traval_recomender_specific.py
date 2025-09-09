from google import genai
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Start chat session
chat = client.chats.create(model="gemini-1.5-flash")

print("Hello! 👋 I can recommend travel destinations in Sri Lanka.")
print("Let's get started.")

# Step 1: Ask for location
location = input("📍 What location do you want to visit? ")

# Step 2: Ask for time/month
time_period = input("🗓️ Which month or time period are you planning your trip? ")

# Step 3: Send both to Gemini
prompt = f"I want to visit {location} in {time_period}. Can you recommend attractions suitable for that time?"

res = chat.send_message(prompt)
print("\n✨ Travel Recommendation:")
print(res.text)
print("\nFeel free to ask more questions or type 'exit' to quit.")