import datetime
import json
from typing import Any, List, Dict
from pydantic import BaseModel  # Added for type hinting clarity on raw outputs

try:
    import bleach
except Exception:
    bleach = None

# LangChain imports are now moved inside the function for lazy loading and clarity
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_openai import ChatOpenAI

from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from server.schemas.summary_schemas import SummaryAgentInputSchema, SummaryAgentOutputSchema


def _get_summary_llm(api_key: str, model_name: str, temperature: float = 0.3):
    """Initializes and returns the ChatOpenAI instance for summarization."""
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(api_key=api_key, model=model_name, temperature=temperature, max_tokens=800)
    except Exception as e:
        print(f"Error initializing LLM: {e}")
        return None

# --- Helper Functions (No change, retained for context) ---
def _bleach_clean(text: str, strip: bool = True) -> str:
    """Use bleach.clean if available, otherwise perform a minimal HTML tag strip."""
    if bleach is not None:
        return bleach.clean(text, strip=strip)
    import re
    if text is None: return ""
    s = str(text)
    s = re.sub(r"<[^>]*>", "", s)
    return s


def _sanitize(val: Any, max_len: int = 1000) -> str:
    """Safely coerce to string, clean HTML and truncate."""
    if val is None: return ""
    if isinstance(val, (dict, list)):
        try:
            s = json.dumps(val, ensure_ascii=False)
        except Exception:
            s = str(val)
    else:
        s = str(val)
    return _bleach_clean(s, strip=True)[:max_len]


def _short(val: Any, max_len: int = 250) -> str:
    s = _sanitize(val, max_len=max_len)
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


# --- Core Function Update ---

def generate_summary(state: SummaryAgentInputSchema | dict, use_llm: bool = True) -> SummaryAgentOutputSchema:
    """
    Generates a refined, conversational summary of the trip
    using the collected information in SummaryAgentInputSchema.
    The summary is creative, accurate, friendly, and adheres to RAI rules.
    """

    print(f"\nDEBUG: Generating summary for state: {state}")

    # --- Data Extraction (Retained) ---
    if isinstance(state, dict):
        _dst = state.get("destination")
        _start = state.get("start_date")
        _end = state.get("end_date")
        _num = state.get("no_of_traveler")
        _budget = state.get("budget")
        _prefs = state.get("user_preferences") or []
        _type = state.get("type_of_trip")
        _locations = state.get("locations_to_visit") or []
        _activities = state.get("activities") or []
        _packing = state.get("packing_list") or []
        _additional = state.get("additional_info")
        _messages = state.get("messages") or []
        _loc_raw = state.get("location_recommendations") or {}
        _act_raw = state.get("activity_recommendations") or {}
    else:
        _dst = state.destination
        _start = state.start_date
        _end = state.end_date
        _num = state.no_of_traveler
        _budget = state.budget
        _prefs = state.user_preferences or []
        _type = state.type_of_trip
        _locations = state.locations_to_visit or []
        _activities = state.activities or []
        _packing = state.packing_list or []
        _additional = state.additional_info
        _messages = state.messages or []
        _loc_raw = getattr(state, "location_recommendations", {}) or {}
        _act_raw = getattr(state, "activity_recommendations", {}) or {}

    # Helper: quickly extract recommended location list if raw provided
    try:
        if _loc_raw and isinstance(_loc_raw, dict):
            recs = _loc_raw.get("recommended_locations") or []
            if recs:
                _locations = [r.get("name") for r in recs if r.get("name")]
    except Exception:
        pass

    # --- Build raw summary parts (structured, human readable) ---
    response_parts: List[str] = []

    # Title and Quick Index (Retained structure)
    if _dst:
        response_parts.append(f"# 🎉 Your Custom Trip to {_short(_dst, 120)}\n")

    index_lines = ["## Quick Links"]
    if _start and _end: index_lines.append("- Dates & Season")
    if _locations: index_lines.append("- Recommended Destinations")
    if _activities: index_lines.append("- Daily Activities")
    if _packing: index_lines.append("- Packing Essentials")
    index_lines.append("- Responsible AI Notes")
    response_parts.extend(index_lines)
    response_parts.append("\n---")

    # Trip Overview (Friendly Introduction)
    if _dst:
        intro = f"## Hello there! Your exciting trip to **{_dst}** is all set. Here's a creative overview of your personalized itinerary:"
        response_parts.append(intro)

    # Dates
    if _start and _end:
        try:
            start_dt = datetime.datetime.strptime(_start, "%Y-%m-%d").strftime("%B %d, %Y")
            end_dt = datetime.datetime.strptime(_end, "%Y-%m-%d").strftime("%B %d, %Y")
            response_parts.append(f"\n## 🗓️ Dates & Season\n- You'll be exploring from **{start_dt}** to **{end_dt}**.")

            # Attempt to pull season from state or infer if possible
            season_text = ""
            if state.get("season"):
                season_text = f" This falls during the **{state['season']}** in Sri Lanka, which is a great time for {('coastal activities on the South/West' if 'Southwest' in state['season'] else 'North/East coast exploration') if 'Monsoon' in state['season'] else 'island-wide travel'}. Be prepared!"
            response_parts.append(f"- Duration: **{start_dt}** to **{end_dt}**.{season_text}")
        except ValueError:
            response_parts.append(f"\n## 🗓️ Dates\n- {_start} → {_end} (Please confirm the date format).\n")

    # Travelers and Type
    traveler_text = "a fantastic solo adventure" if _num == 1 else f"a wonderful journey for **{_num} people**"
    type_text = f" as a **{_type}** trip" if _type else ""
    budget_text = f" with a **{str(_budget).capitalize()}** budget" if _budget else ""

    response_parts.append(f"\n## 👥 Who's Traveling?\n- This is planned as {traveler_text}{type_text}{budget_text}.")

    # Preferences
    if _prefs:
        prefs = ", ".join([p.capitalize() for p in _prefs])
        response_parts.append(f"\n## 🎯 Your Vibe\n- We've focused the itinerary around your interests in: **{prefs}**.")

    # Locations
    if _loc_raw and isinstance(_loc_raw, dict) and _loc_raw.get("recommended_locations"):
        response_parts.append("\n## 🗺️ Recommended Destinations")
        for loc in _loc_raw.get("recommended_locations", []):
            name = _short(loc.get("name"))
            ltype = _short(loc.get("type"))
            reason = _short(loc.get("reason"), max_len=600)
            response_parts.append(f"- **{name}** ({ltype}): {reason}")
        response_parts.append("")
    elif _locations:
        response_parts.append("\n## 🗺️ Recommended Destinations")
        response_parts.append(f"- Destinations include: {', '.join([_short(loc) for loc in _locations])}")
        response_parts.append("")

    # Activities
    if _act_raw and isinstance(_act_raw, dict) and _act_raw.get("day_plans"):
        response_parts.append("\n## 🎡 Daily Activities")
        for day in _act_raw.get("day_plans", []):
            date = day.get("date", "")
            response_parts.append(f"### 📅 {date}")
            for sug in day.get("suggestions", []):
                tod = sug.get("time_of_day", "")
                title = _short(sug.get("title"), max_len=200)
                why = _short(sug.get("why"), max_len=400)
                response_parts.append(f"- **{tod.capitalize()}**: {title} — *{why}*")
            response_parts.append("")
    elif _activities:
        response_parts.append("\n## 🎡 Key Activities")
        for act in _activities:
            response_parts.append(f"- {_short(act)}")
        response_parts.append("")

    # Packing List (Retained logic for structured rendering)
    if _packing:
        response_parts.append("\n## 🎒 Suggested Packing List")
        try:
            if hasattr(_packing, "model_dump"):
                packing_obj = _packing.model_dump()
            elif isinstance(_packing, dict):
                packing_obj = _packing
            else:
                packing_obj = None
        except Exception:
            packing_obj = None

        if packing_obj and isinstance(packing_obj, dict) and packing_obj.get("categories"):
            for cat in packing_obj.get("categories", []):
                cat_name = cat.get("name") or ""
                if cat_name: response_parts.append(f"### {cat_name}")
                for it in cat.get("items", []):
                    if isinstance(it, dict):
                        name, reason = it.get("name"), it.get("reason")
                        response_parts.append(f"- {name} {'— ' + reason if reason else ''}")
                    else:
                        response_parts.append(f"- {it}")
                response_parts.append("")
        else:
            for item in _packing: response_parts.append(f"- {item}")
            response_parts.append("")

    if _additional:
        response_parts.append("\n## ℹ️ Extra Details\n")
        response_parts.append(f"{_short(_additional, max_len=800)}\n")

    # --- Responsible AI & Disclaimers (Enhanced) ---
    response_parts.append("\n---\n## 🔒 Responsible AI & Data Notes (Mandatory)")
    response_parts.append(
        "- **Accuracy Disclaimer**: This itinerary is AI-generated based on the provided data. Please **always verify** dates, opening hours, travel advisories, and prices before booking or departing.")
    response_parts.append(
        "- **Safety First**: Prioritize local guidance and official travel warnings. This system is for planning only and is **not a substitute for professional advice**.")
    response_parts.append(
        "- **Bias Mitigation**: Recommendations aim to be diverse but may reflect patterns in available data. If you notice bias or a preference for a certain area/activity, please provide feedback.")
    response_parts.append(
        "- **Privacy**: No personal identifying information (beyond what you explicitly typed) is stored in this summary output.")

    # Source and status notes (Retained)
    try:
        loc_status = _loc_raw.get("status") if isinstance(_loc_raw, dict) else None
        act_status = _act_raw.get("status") if isinstance(_act_raw, dict) else None
        if loc_status or act_status:
            response_parts.append(
                f"- **Agent Status**: Location planning: {loc_status if loc_status else 'N/A'}, Activity planning: {act_status if act_status else 'N/A'}")
    except Exception:
        pass

    raw_summary = "\n".join(response_parts)

    # --- LLM Refinement (Updated Prompt) ---
    if not use_llm:
        return SummaryAgentOutputSchema(summary=raw_summary, status="completed",
                                        messages=_messages + [{"role": "assistant", "content": raw_summary}])

    if use_llm:
        try:
            # lazy imports
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            # from langchain_openai import ChatOpenAI # Removed this import, using _get_summary_llm

            summary_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a friendly and professional trip planning assistant. 
                    Refine the provided raw trip summary into a clear, well-structured Markdown document. 
                    ... (rest of the prompt remains the same) ...
                    Do NOT share private info. Do NOT share harmful info."""),
                ("human", "Here is the raw trip summary:\n{raw_info}")
            ])

            # Use the new helper to create LLM lazily
            llm = _get_summary_llm(api_key=OPENAI_API_KEY, model_name=OPENAI_MODEL, temperature=0.3)
            if llm is None:
                raise Exception("LLM failed to initialize.")

            summary_chain = summary_prompt | llm | StrOutputParser()

            final_summary = summary_chain.invoke({"raw_info": raw_summary})

            print(f"\nDEBUG: Final polished summary: {final_summary}")

            return SummaryAgentOutputSchema(
                summary=final_summary,
                status="completed",
                messages=_messages + [{"role": "assistant", "content": final_summary}]
            )
        except Exception as e:
            fallback_msg = f"⚠️ I encountered an error creating the polished summary: {e}. Here’s the raw summary instead:\n\n{raw_summary}"
            return SummaryAgentOutputSchema(
                summary=fallback_msg,
                status="error",
                messages=_messages + [{"role": "assistant", "content": fallback_msg}]
            )

        # Fallback (Retained)
        else:
            return SummaryAgentOutputSchema(
                summary=raw_summary,
                status="completed",
                messages=_messages + [{"role": "assistant", "content": raw_summary}],
            )