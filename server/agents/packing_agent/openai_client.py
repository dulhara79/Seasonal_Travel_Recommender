import os, json
from openai import OpenAI

from server.utils.config import OPENAI_API_KEY, LLM_MODEL

def call_chat_completion(messages, model=None, temperature=0.3, max_tokens=600):
    """
    
    Thin wrapper around OpenAI Chat Completions for portability.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)
    model = LLM_MODEL
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "text"}  # we’ll parse JSON ourselves
    )
    return resp.choices[0].message.content
