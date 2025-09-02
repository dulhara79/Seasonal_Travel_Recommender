from google import genai
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Create chat session
chat = client.chats.create(model="gemini-1.5-flash")  # use a valid model

# Interactive loop
while True:
    message = input("> ")
    if message.lower() == "exit":
        break

    res = chat.send_message(message)
    print("\nsenuvi:", res.text)
