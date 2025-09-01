# from datetime import datetime
# from typing import Optional, Tuple
# import dateparser
#
# def normalize_dates(free_text: str) -> Tuple[Optional[str], Optional[str]]:
#     """
#     Attempts to parse a date range like 'Dec 15–20' or 'from Dec 15 to Dec 20' (any year).
#     Returns (start_iso, end_iso).
#     """
#     # Try a few heuristics
#     text = free_text.replace("–", "-").replace("—", "-")
#     # Check for patterns like "from X to Y"
#     # Fallback: find two dates in text
#     dates = dateparser.search.search_dates(text, settings={"PREFER_DATES_FROM": "future"})
#     if not dates or len(dates) == 0:
#         return None, None
#     # Pick first two distinct dates
#     uniq = []
#     for _, dt in dates:
#         dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
#         if not uniq or (uniq and dt.date() != uniq[-1].date()):
#             uniq.append(dt)
#         if len(uniq) == 2:
#             break
#     if len(uniq) == 1:
#         s = uniq[0].date().isoformat()
#         return s, s
#     if len(uniq) >= 2:
#         s = min(uniq[0], uniq[1]).date().isoformat()
#         e = max(uniq[0], uniq[1]).date().isoformat()
#         return s, e
#     return None, None
#
# def iso_or_none(dt) -> Optional[str]:
#     try:
#         return datetime.fromisoformat(dt).date().isoformat()
#     except Exception:
#         return None
#
# def pretty_date(iso: Optional[str]) -> Optional[str]:
#     if not iso:
#         return None
#     return datetime.fromisoformat(iso).strftime("%b %d, %Y")
#
# def join_nonempty(parts):
#     return ", ".join([p for p in parts if p])

# convo_orchestrator/utils.py
import httpx
import os
from typing import Any, Dict, Optional
import time

DEFAULT_TIMEOUT = 10.0
RETRIES = 2
BACKOFF = 0.5

async def post_json_with_retry(url: str, payload: Dict[str, Any], headers: Optional[Dict[str,str]] = None, timeout: float = DEFAULT_TIMEOUT):
    last_exc = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(RETRIES + 1):
            try:
                r = await client.post(url, json=payload, headers=headers or {})
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_exc = e
                if attempt < RETRIES:
                    time.sleep(BACKOFF * (2 ** attempt))
                else:
                    raise
