# import json
# from datetime import datetime
# from typing import Any, Dict, List, Optional
# import bleach
#
# from .prompt import SYSTEM_PROMPT, build_user_prompt
# from .openai_client import call_chat_completion
# from .rules import rule_based_pack, fairness_sort
#
#
# def sanitize(s: str, max_len: int = 300) -> str:
#     s = bleach.clean(s or "", strip=True)
#     return s[:max_len]
#
# def days_between(start: str, end: str) -> int:
#     try:
#         sd = datetime.fromisoformat(start)
#         ed = datetime.fromisoformat(end)
#         return max(1, (ed - sd).days + 1)
#     except Exception:
#         return 1
#
# def to_model_payload(activity_input: Dict[str, Any], suggested_activities: List[str]) -> Dict[str, Any]:
#     """
#     Build a minimal, injection-safe payload for the LLM from your incoming JSON.
#     """
#     return {
#         "location": sanitize(activity_input.get("location")),
#         "season": sanitize(activity_input.get("season")),
#         "start_date": sanitize(activity_input.get("start_date")),
#         "end_date": sanitize(activity_input.get("end_date")),
#         "duration_days": days_between(activity_input.get("start_date"), activity_input.get("end_date")),
#         "no_of_traveler": int(activity_input.get("no_of_traveler", 1) or 1),
#         "budget": sanitize(activity_input.get("budget", "")),
#         "type_of_trip": sanitize(activity_input.get("type_of_trip", "")),
#         "user_preferences": [sanitize(x) for x in (activity_input.get("user_preferences") or [])],
#         "suggest_locations": [sanitize(x) for x in (activity_input.get("suggest_locations") or [])],
#         "suggested_activities": [sanitize(x) for x in (suggested_activities or [])],
#     }
#
# def parse_strict_json(s: str) -> Optional[Dict[str, Any]]:
#     # Try strict parse; if model added text, attempt to find the first {...} block
#     try:
#         return json.loads(s)
#     except Exception:
#         pass
#     try:
#         start = s.find("{")
#         end = s.rfind("}")
#         if start != -1 and end != -1 and end > start:
#             return json.loads(s[start:end+1])
#     except Exception:
#         return None
#
# def generate_packing_list(activity_input: Dict[str, Any], suggested_activities: List[str], use_llm: bool = True) -> Dict[str, Any]:
#     """
#     Main entry point: returns a structured packing JSON.
#     - If OPENAI key is set and use_llm=True, try LLM.
#     - Always post-process with fairnessSort and minimal validations.
#     - If LLM fails, fall back to deterministic rule-based list.
#     """
#     payload = to_model_payload(activity_input, suggested_activities)
#
#     llm_result = None
#     if use_llm:
#         try:
#             messages = [
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": build_user_prompt(payload)}
#             ]
#             raw = call_chat_completion(messages)
#             cand = parse_strict_json(raw)
#             if cand and "categories" in cand:
#                 llm_result = cand
#         except Exception as e:
#             llm_result = None
#
#     if not llm_result:
#         # Deterministic fallback
#         rb = rule_based_pack(payload["season"], payload["suggested_activities"])
#         rb["duration_days"] = payload["duration_days"]
#         rb["categories"] = fairness_sort(rb["categories"])
#         return rb
#
#     # Normalize LLM output and apply fairness sorting
#     llm_result["duration_days"] = payload["duration_days"]
#     llm_result["categories"] = fairness_sort(llm_result.get("categories", []))
#     return llm_result



# server/agents/packing_agent/packing_agent.py

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import bleach

from .prompt import SYSTEM_PROMPT, build_user_prompt
from .openai_client import call_chat_completion
from .rules import rule_based_pack, fairness_sort

from server.schemas.global_schema import TravelState, PackingOutput


def sanitize(value: Any, max_len: int = 300) -> str:
    """
    Coerce any input to a text string safe for bleach.clean:
    - None -> ''
    - dict/list -> JSON string
    - other types -> str(...)
    Then run bleach.clean on the resulting text and truncate to max_len.
    """
    if value is None:
        text = ""
    elif isinstance(value, (dict, list)):
        try:
            text = json.dumps(value, ensure_ascii=False)
        except Exception:
            text = str(value)
    else:
        text = str(value)
    cleaned = bleach.clean(text, strip=True)
    return cleaned[:max_len]


def days_between(start: Optional[str], end: Optional[str]) -> int:
    try:
        if not start or not end:
            return 1
        sd = datetime.fromisoformat(start)
        ed = datetime.fromisoformat(end)
        return max(1, (ed.date() - sd.date()).days + 1)
    except Exception:
        return 1


def to_model_payload(state_input: Dict[str, Any], suggested_activities: Optional[List[Any]] = None) -> Dict[str, Any]:
    """
    Normalize a state dict (from TravelState.dict() or raw dict) into the minimal,
    sanitized payload expected by the prompt builder / LLM.
    """
    suggested = suggested_activities or state_input.get("activities") or state_input.get("suggested_activities") or []

    return {
        "location": sanitize(state_input.get("destination") or state_input.get("location")),
        "season": sanitize(state_input.get("season")),
        "start_date": sanitize(state_input.get("start_date")),
        "end_date": sanitize(state_input.get("end_date")),
        "duration_days": days_between(state_input.get("start_date"), state_input.get("end_date")),
        "no_of_traveler": int(state_input.get("no_of_traveler", 1) or 1),
        "budget": sanitize(state_input.get("budget", "")),
        "type_of_trip": sanitize(state_input.get("type_of_trip", "")),
        "user_preferences": [sanitize(x) for x in (state_input.get("user_preferences") or [])],
        "suggest_locations": [sanitize(x) for x in (state_input.get("locations_to_visit") or state_input.get("suggest_locations") or [])],
        "suggested_activities": [sanitize(x) for x in (suggested or [])],
    }


def parse_strict_json(s: str) -> Optional[Dict[str, Any]]:
    # Try strict parse; if model added text, attempt to find the first {...} block
    try:
        return json.loads(s)
    except Exception:
        pass
    try:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(s[start:end + 1])
    except Exception:
        return None


def generate_packing_list(
    state_input: Union[Dict[str, Any], TravelState],
    suggested_activities: Optional[List[Any]] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    Accepts either a TravelState instance or a dict compatible with TravelState.
    Returns a plain dict (compatible with callers that use .get()).

    - Normalizes input from TravelState fields.
    - If use_llm=True and an LLM response parsable to the expected schema is available, use it.
    - Otherwise fall back to deterministic rule_based_pack and apply fairness_sort.
    """
    # Normalize incoming state to a dict
    if isinstance(state_input, TravelState):
        state_dict = state_input.dict()
    elif isinstance(state_input, dict):
        state_dict = state_input
    else:
        raise TypeError("state_input must be TravelState or dict")

    payload = to_model_payload(state_dict, suggested_activities)

    llm_result: Optional[Dict[str, Any]] = None
    if use_llm:
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(payload)},
            ]
            raw = call_chat_completion(messages)
            cand = parse_strict_json(raw or "")
            if cand and "categories" in cand:
                llm_result = cand
        except Exception:
            llm_result = None

    if not llm_result:
        # Deterministic fallback
        rb = rule_based_pack(payload["season"], payload["suggested_activities"])
        rb["duration_days"] = payload["duration_days"]
        rb["categories"] = fairness_sort(rb.get("categories", []))
        # Return a dict for compatibility with graph_builder and other callers
        return PackingOutput(**rb).dict()

    # Normalize LLM output and apply fairness sorting
    llm_result["duration_days"] = payload["duration_days"]
    llm_result["categories"] = fairness_sort(llm_result.get("categories", []))
    if "notes" not in llm_result:
        llm_result["notes"] = []

    print(f"\nDEBUG: Packing LLM output:\n{json.dumps(llm_result, indent=2, ensure_ascii=False)}\n")

    # Return a dict for compatibility with graph_builder and other callers
    return PackingOutput(**llm_result).dict()