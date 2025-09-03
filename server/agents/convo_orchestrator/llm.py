# llm.py (minor tweak)
import os
from typing import Optional
from utils.config import OPENAI_API_KEY, LLM_MODEL

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

_client = None

def _get_client() -> Optional[OpenAI]:
    global _client
    if _client is None:
        key = OPENAI_API_KEY

        if not key or OpenAI is None:
            return None
        _client = OpenAI(api_key=key)
    return _client

def polish_response(system_prompt: str, draft: str) -> Optional[str]:
    client = _get_client()
    if client is None:
        return None
    try:
        # adapt call to your installed OpenAI SDK if necessary
        res = client.chat.completion.create(
            model=LLM_MODEL,
            temperature=0.3,
            message=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': draft}
            ],
        )
        return res.choices[0].message.content
    except Exception as e:
        print("LLM polish failed:", e)
        return None
