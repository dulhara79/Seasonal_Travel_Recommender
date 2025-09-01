# import re
# from fastapi import HTTPException, status
# from typing import Optional
#
# SAFE_TEXT_PATTERNS = re.compile(r"^[\s\S]{0,2000}$")
#
# def sanitize_input(text: str) -> str:
#     # input size validation
#     if not SAFE_TEXT_PATTERNS.match(text):
#         raise HTTPException(
#             status_code = status.HTTP_400_BAD_REQUEST,
#             detail = 'Invalid Input Size.'
#         )
#     # remove script tags and URIs
#     text = re.sub(r"(?i)<\s*script.*?>.*?<\s*/\s*script\s*>", "", text)
#     text = re.sub(r"(?i)javascript:", "", text)
#
#     return text
#
# # Auth check function
# # def check_user_auth(user_id: str, token: str) -> Optional[HTTPException]:
# #     if not user_id or not token:
# #         return HTTPException(
# #             status_code=status.HTTP_401_UNAUTHORIZED,
# #             detail="Invalid authentication credentials."
# #         )
# #     # Further validation logic can be added here
# #     return None

# convo_orchestrator/security.py
import os
from fastapi import HTTPException, Header

SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "changeme")

def authorize(authorization: str = Header(None)):
    """
    Simple bearer token auth for clients. Replace with OAuth/JWT for prod.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or missing token")
    return True
