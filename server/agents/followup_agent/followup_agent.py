# python
from typing import Dict, Tuple, List, Optional

from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
import os
import json
from difflib import get_close_matches
from typing import Any
from server.utils.config import GEOCODER_ENABLE, GEOCODER_USER_AGENT, GEOCODER_CACHE_PATH
import threading


class FollowUpAgent:
    def __init__(self, question_templates: Optional[Dict[str, str]] = None,
                 mandatory_fields: Optional[List[str]] = None):
        self.question_templates = question_templates or {
            "destination": "🌍 Where would you like to travel?",
            "start_date": "📅 What is your trip start date? (YYYY-MM-DD)",
            "end_date": "📅 What is your trip end date? (YYYY-MM-DD)",
            "no_of_traveler": "👥 How many people are traveling?",
            "type_of_trip": "🎯 What type of trip is this (leisure, adventure, business, family)?",
            "budget": "💰 What is your budget (low, medium, high)?",
            "user_preferences": "✨ Any preferences? (e.g., beach, culture, food) — comma separated"
        }
        self.mandatory_fields = mandatory_fields or ["destination", "start_date", "end_date", "no_of_traveler",
                                                     "type_of_trip"]
        self.llm_api_key = OPENAI_API_KEY
        self.llm_model = OPENAI_MODEL
        # Load canonical Sri Lanka place list for fuzzy matching
        try:
            data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sri_lanka_places.json")
            with open(data_path, "r", encoding="utf-8") as f:
                j = json.load(f)
                self._sri_places_list = [p for p in j.get("places", []) if isinstance(p, str)]
        except Exception:
            self._sri_places_list = []

    def _is_missing(self, val) -> bool:
        return val in (None, "", [], 0)

    def _is_sri_lanka_place(self, place: str) -> bool:
        """Basic heuristic: check if the provided place string mentions Sri Lanka or known Sri Lankan locations.
        This is intentionally simple — for higher quality use a geo/lookup service later.
        """
        if not place or not isinstance(place, str):
            return False
        low = place.lower()
        # Quick substring check against list if loaded
        for p in self._sri_places_list:
            if p.lower() in low:
                return True
        # last-resort substring heuristic
        sri_places = ["sri lanka", "colombo", "galle", "kandy", "ella", "sigiriya", "nuwara eliya", "trincomalee", "mirissa", "arugam bay", "anuradhapura", "polonnaruwa"]
        return any(x in low for x in sri_places)

    def _match_sri_lanka_place(self, place: str, cutoff: float = 0.7) -> Any:
        """Return a canonical match from the sri_places_list if close enough, otherwise None."""
        if not place or not isinstance(place, str) or not self._sri_places_list:
            return None
        # Use difflib to find close matches
        candidates = get_close_matches(place, self._sri_places_list, n=3, cutoff=cutoff)
        if candidates:
            return candidates[0]
        return None

    # --- Optional Nominatim geocoding helpers ---
    def _load_geocode_cache(self) -> Dict[str, Any]:
        try:
            if os.path.exists(GEOCODER_CACHE_PATH):
                with open(GEOCODER_CACHE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_geocode_cache(self, cache: Dict[str, Any]):
        try:
            dirp = os.path.dirname(GEOCODER_CACHE_PATH)
            if dirp and not os.path.exists(dirp):
                os.makedirs(dirp, exist_ok=True)
            with open(GEOCODER_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _geocode_place(self, place: str) -> Optional[Dict[str, Any]]:
        """Perform a lightweight Nominatim lookup for `place`. Returns geocoded record or None.
        This is only attempted when GEOCODER_ENABLE is True. Results are cached in GEOCODER_CACHE_PATH.
        """
        if not GEOCODER_ENABLE:
            return None
        if not place or not isinstance(place, str):
            return None

        key = place.strip().lower()
        cache = self._load_geocode_cache()
        if key in cache:
            return cache.get(key)

        # Lazy import httpx to avoid hard dependency at module import time
        try:
            import httpx
        except Exception:
            return None

        params = {"q": place, "format": "json", "addressdetails": 1, "limit": 3, "countrycodes": "lk"}
        headers = {"User-Agent": GEOCODER_USER_AGENT}
        try:
            with httpx.Client(timeout=5.0, headers=headers) as client:
                resp = client.get("https://nominatim.openstreetmap.org/search", params=params)
                if resp.status_code == 200:
                    j = resp.json()
                    if isinstance(j, list) and j:
                        # pick the first result with address.country_code == 'lk'
                        for item in j:
                            addr = item.get("address") or {}
                            if addr.get("country_code") == "lk":
                                # cache and return
                                cache[key] = item
                                # Save cache asynchronously to avoid blocking
                                t = threading.Thread(target=self._save_geocode_cache, args=(cache,))
                                t.daemon = True
                                t.start()
                                return item
        except Exception:
            return None

        # negative cache to avoid repeated lookups
        try:
            cache[key] = None
            self._save_geocode_cache(cache)
        except Exception:
            pass
        return None

    def _validate_date(self, date_str: str) -> bool:
        """Validate YYYY-MM-DD format and that it's not obviously malformed."""
        from datetime import datetime
        if not date_str or not isinstance(date_str, str):
            return False
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except Exception:
            return False

    def _is_past_date(self, date_str: str) -> bool:
        from datetime import datetime, date
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            return d < date.today()
        except Exception:
            return False

    def _make_question(self, field: str, context: str = "") -> str:
        if field in self.question_templates:
            return self.question_templates[field]
        base = f"Could you provide the {field.replace('_', ' ')}?"
        if context:
            base += f" (Context: {context[:100] + '...' if len(context) > 100 else context})"
        return base

    def collect(
            self,
            additional_info: str = "",
            followup_answers: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict[str, object], Dict[str, str]]:
        followup_answers = followup_answers or {}
        fields: Dict[str, object] = {}
        missing_questions: Dict[str, str] = {}

        for f in self.mandatory_fields:
            val = followup_answers.get(f)
            if val is not None and not self._is_missing(val):
                # Field-specific normalization and validation
                if f == "no_of_traveler":
                    try:
                        val = int(val)
                    except Exception:
                        pass
                if f in ("user_preferences", "preferences") and isinstance(val, str):
                    val = [p.strip() for p in val.split(",") if p.strip()]
                if f == "destination":
                    # Validate Sri Lanka location. Prefer fuzzy match from the local list,
                    # then optionally fall back to a Nominatim geocode (country code == 'lk').
                    if isinstance(val, str):
                        matched = None
                        try:
                            if self._is_sri_lanka_place(val):
                                matched = self._match_sri_lanka_place(val)
                        except Exception:
                            matched = None

                        # If no good fuzzy match found, try geocoding (if enabled)
                        if not matched:
                            try:
                                geo = self._geocode_place(val)
                                if geo:
                                    addr = geo.get("address") or {}
                                    # prefer local administrative/place name fields
                                    for k in ("city", "town", "village", "municipality", "county", "state", "region"):
                                        if addr.get(k):
                                            matched = addr.get(k)
                                            break
                                    if not matched:
                                        matched = geo.get("display_name")
                            except Exception:
                                matched = None

                        if matched:
                            val = matched
                        else:
                            # leave it out so followup will ask for Sri Lanka-specific destination
                            val = None
                if f in ("start_date", "end_date"):
                    if isinstance(val, str):
                        # Validate format
                        if not self._validate_date(val):
                            val = None
                        else:
                            # if date is in the past, reject and ask explicitly
                            if self._is_past_date(val):
                                val = None
                fields[f] = val

        for f in self.mandatory_fields:
            if f in fields and not self._is_missing(fields[f]):
                continue
            # Add field-specific prompting guidance if we detected an invalid value previously
            context = additional_info
            if f == "destination":
                # If user provided a non-Sri-Lanka place in followup_answers, ask to choose Sri Lanka location
                provided = followup_answers and followup_answers.get(f)
                if provided and isinstance(provided, str) and not self._is_sri_lanka_place(provided):
                    q = f"We currently only support travel within Sri Lanka. Please enter a destination within Sri Lanka (e.g. Colombo, Kandy, Galle). You entered: '{provided}'."
                    missing_questions[f] = q
                    continue
            if f in ("start_date", "end_date"):
                provided = followup_answers and followup_answers.get(f)
                if provided and isinstance(provided, str) and not self._validate_date(provided):
                    q = f"Please provide the {f.replace('_', ' ')} in YYYY-MM-DD format. You entered: '{provided}'."
                    missing_questions[f] = q
                    continue
                if provided and isinstance(provided, str) and self._is_past_date(provided):
                    q = f"The {f.replace('_', ' ')} appears to be in the past: '{provided}'. Please provide a future date."
                    missing_questions[f] = q
                    continue

            q = self._make_question(f, context)
            missing_questions[f] = q

        return fields, missing_questions


def create_followup_questions(json_response: Dict, missing_fields: List[str],
                              followup_answers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Compatibility wrapper used by orchestrator_agent.

    Args:
        json_response: current orchestrator json state (may contain 'additional_info').
        missing_fields: list of fields orchestrator needs questions for.
        followup_answers: optional previously collected answers.

    Returns:
        dict mapping field -> question (only for fields listed in missing_fields).
    """
    additional_info = ""
    if isinstance(json_response, dict):
        additional_info = json_response.get("additional_info") or json_response.get("query") or ""

    agent = FollowUpAgent()
    _, missing_questions = agent.collect(additional_info=additional_info, followup_answers=followup_answers or {})

    # Return only requested missing fields, preserving order if possible
    return {f: missing_questions[f] for f in missing_fields if f in missing_questions}
