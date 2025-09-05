import os, json
from openai import OpenAI

def call_chat_completion(messages, model=None, temperature=0.3, max_tokens=600):
    """
    Thin wrapper around OpenAI Chat Completions for portability.
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "text"}  # we’ll parse JSON ourselves
    )
    return resp.choices[0].message.content
