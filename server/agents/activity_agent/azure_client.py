# Handles Azure LLM authentication and API calls


# Encapsulates Azure API key, endpoint, model selection, and actual LLM call.


import openai
import os

# Set up your API key and endpoint
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_API_ENDPOINT")

def get_activity_suggestions(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

