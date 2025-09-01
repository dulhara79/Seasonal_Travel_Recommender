# import os
# from typing import Optional
# from openai import OpenAI
#
# _client = None
#
# def _get_client() -> Optional[OpenAI]:
#     key = os.getenv("OPENAI_API_KEY")
#     if not key:
#         return None
#
#     global _client
#     if _client is None:
#         _client = OpenAI(api_key=key)
#
#     return _client
#
# def polish_response(system_prompt: str, draft: str) -> Optional[str]:
#     client = _get_client()
#     if client is None:
#         return None
#
#     try:
#         res = client.chat.completion.create(
#             model='gpt-40-mini',  # type: ignore,
#             temperature=0.3,
#             message=[
#                 {'role': 'system', 'content': system_prompt},
#                 {'role': 'user', 'content': draft}
#             ],
#         )
#         return res.choices[0].message.content
#     except Exception as e:
#         print(e)
#         return None
