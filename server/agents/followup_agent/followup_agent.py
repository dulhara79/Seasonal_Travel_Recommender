# python
from typing import Dict, Tuple, List, Optional

from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL


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

    def _is_missing(self, val) -> bool:
        return val in (None, "", [], 0)

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
                if f == "no_of_traveler":
                    try:
                        val = int(val)
                    except Exception:
                        pass
                if f in ("user_preferences", "preferences") and isinstance(val, str):
                    val = [p.strip() for p in val.split(",") if p.strip()]
                fields[f] = val

        for f in self.mandatory_fields:
            if f in fields and not self._is_missing(fields[f]):
                continue
            q = self._make_question(f, additional_info)
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
