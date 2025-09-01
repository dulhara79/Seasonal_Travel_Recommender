import os
from dotenv import load_dotenv
from google import genai

# Load the .env file
load_dotenv()

# Get your API key
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="can you recommend me place to go in Kandy in December as someone who loves to hike?"
)

print(response.text)
