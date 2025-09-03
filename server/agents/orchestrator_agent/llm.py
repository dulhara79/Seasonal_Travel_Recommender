# llm.py
import os
import openai
from utils.config import OPENAI_API_KEY, LLM_MODEL

openai.api_key = OPENAI_API_KEY

def chat_completion(messages, model=LLM_MODEL, temperature=0.7):
    """
    messages: list of {"role": "user"/"assistant"/"system", "content": "..."}
    """
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"LLM error: {str(e)}"
