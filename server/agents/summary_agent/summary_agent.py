import datetime
import json
from typing import Any, List

try:
    import bleach
except Exception:
    bleach = None

from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from server.schemas.summary_schemas import SummaryAgentInputSchema, SummaryAgentOutputSchema


def _bleach_clean(text: str, strip: bool = True) -> str:
    """Use bleach.clean if available, otherwise perform a minimal HTML tag strip."""
    if bleach is not None:
        return bleach.clean(text, strip=strip)
    # Minimal fallback: remove anything between angle brackets
    import re

    if text is None:
        return ""
    s = str(text)
    s = re.sub(r"<[^>]*>", "", s)
    return s


# LLM is created lazily inside generate_summary when use_llm=True


def _sanitize(val: Any, max_len: int = 1000) -> str:
    """Safely coerce to string, clean HTML and truncate."""
    if val is None:
        return ""
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


def generate_summary(state: SummaryAgentInputSchema | dict, use_llm: bool = True) -> SummaryAgentOutputSchema:
    """
    Generates a refined, conversational summary of the trip
    using the collected information in SummaryAgentInputSchema.
    """

    print(f"\nDEBUG: Generating summary for state: {state}")

    # Normalize incoming state to work with either a pydantic object or a
    # plain dict returned by lightweight/optional workflow implementations.
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
        # Raw agent outputs (prefer these for detail)
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
            # if locations list empty but locations_to_visit has values, keep those
            if recs:
                _locations = [r.get("name") for r in recs if r.get("name")]
    except Exception:
        pass

    # --- Build raw summary parts (structured, human readable) ---
    response_parts: List[str] = []

    # Top: Title and quick-find index
    if _dst:
        response_parts.append(f"# ✈️ Trip Summary for {_short(_dst, 120)}\n")

    # Quick-find index for easy scanning
    index_lines = ["## Quick find"]
    if _start and _end:
        index_lines.append("- Dates")
    if _locations:
        index_lines.append("- Locations to Visit")
    if _activities:
        index_lines.append("- Activities")
    if _packing:
        index_lines.append("- Packing List")
    if _additional:
        index_lines.append("- Additional Info")
    index_lines.append("- Responsible AI notes")
    response_parts.extend(index_lines)
    response_parts.append("")

    if _dst:
        response_parts.append(f"# ✈️ Trip Summary for {_dst}\n")

    if _start and _end:
        try:
            start_dt = datetime.datetime.strptime(_start, "%Y-%m-%d").strftime("%B %d, %Y")
            end_dt = datetime.datetime.strptime(_end, "%Y-%m-%d").strftime("%B %d, %Y")
            response_parts.append(f"## 🗓️ Dates\n- From **{start_dt}** to **{end_dt}**\n")
        except ValueError:
            response_parts.append(f"## 🗓️ Dates\n- {_start} → {_end} (format issue)\n")

    if _num:
        traveler_text = "solo" if _num == 1 else f"{_num} travelers"
        response_parts.append(f"## 👥 Travelers\n- This trip is planned for **{traveler_text}**\n")

    if _budget:
        try:
            budget_text = _budget.capitalize()
        except Exception:
            budget_text = str(_budget)
        response_parts.append(f"## 💰 Budget\n- Budget level: **{budget_text}**\n")

    if _prefs:
        prefs = ", ".join(_prefs)
        response_parts.append(f"## 🎯 Preferences\n- Your main interests: **{prefs}**\n")

    if _type:
        response_parts.append(f"## 🌍 Trip Type\n- You described this as a **{_type}** trip.\n")

    if _loc_raw and isinstance(_loc_raw, dict) and _loc_raw.get("recommended_locations"):
        response_parts.append("## 🗺️ Locations to Visit — Details")
        for loc in _loc_raw.get("recommended_locations", []):
            name = _short(loc.get("name"))
            ltype = _short(loc.get("type"))
            reason = _short(loc.get("reason"), max_len=600)
            response_parts.append(f"- **{name}** ({ltype}) — {reason}")
        response_parts.append("")
    elif _locations:
        response_parts.append("## 🗺️ Locations to Visit")
        for loc in _locations:
            response_parts.append(f"- {_short(loc)}")
        response_parts.append("")

    # Activities: prefer raw agent day_plans for per-day structured details
    if _act_raw and isinstance(_act_raw, dict) and _act_raw.get("day_plans"):
        response_parts.append("## 🎡 Activities — Day plans")
        for day in _act_raw.get("day_plans", []):
            date = day.get("date", "")
            response_parts.append(f"### {date}")
            for sug in day.get("suggestions", []):
                tod = sug.get("time_of_day", "")
                title = _short(sug.get("title"), max_len=200)
                why = _short(sug.get("why"), max_len=400)
                hints = sug.get("source_hints") or []
                hint_txt = f" (source: {', '.join(hints)})" if hints else ""
                response_parts.append(f"- **{tod.capitalize()}**: {title} — {why}{hint_txt}")
            response_parts.append("")
    elif _activities:
        response_parts.append("## 🎡 Activities")
        for act in _activities:
            response_parts.append(f"- {_short(act)}")
        response_parts.append("")

    if _packing:
        # Normalize packing information: accept either a list of strings (legacy)
        # or the structured PackingOutput / dict with categories/items.
        response_parts.append("## 🎒 Suggested Packing List")

        # If packing is a Pydantic model or dict with 'categories', render items by category
        try:
            # If it's a Pydantic model, convert to dict
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
                if cat_name:
                    response_parts.append(f"### {cat_name}")
                for it in cat.get("items", []):
                    # Each item may be a dict with name/reason or a string
                    if isinstance(it, dict):
                        name = it.get("name")
                        reason = it.get("reason")
                        if reason:
                            response_parts.append(f"- {name} — {reason}")
                        else:
                            response_parts.append(f"- {name}")
                    else:
                        response_parts.append(f"- {it}")
                response_parts.append("")
        else:
            # Fallback: assume it's an iterable of strings
            for item in _packing:
                response_parts.append(f"- {item}")
            response_parts.append("")

    if _additional:
        response_parts.append("## ℹ️ Additional Info")
        response_parts.append(f"{_short(_additional, max_len=800)}\n")

    # Responsible AI notes: data privacy, sources, status & disclaimers
    response_parts.append("## 🔒 Responsible AI & Data Notes")
    # Data handling notice
    response_parts.append("- This summary was generated using automated agents. No personal data is stored in outputs unless explicitly provided by you.")
    # Source and status notes
    try:
        loc_status = _loc_raw.get("status") if isinstance(_loc_raw, dict) else None
        act_status = _act_raw.get("status") if isinstance(_act_raw, dict) else None
        if loc_status:
            response_parts.append(f"- Location agent status: {loc_status}")
        if act_status:
            response_parts.append(f"- Activity agent status: {act_status}")
    except Exception:
        pass
    # Source hints (if any)
    try:
        loc_sources = []
        for r in (_loc_raw.get("recommended_locations") or []):
            s = r.get("source") if isinstance(r, dict) else None
            if s:
                loc_sources.append(_short(s, max_len=200))
        if loc_sources:
            response_parts.append(f"- Location sources (sample): {', '.join(loc_sources[:3])}")
    except Exception:
        pass

    response_parts.append("")

    raw_summary = "\n".join(response_parts)

    # If caller asks to skip the LLM (tests / offline), return the raw summary
    if not use_llm:
        return SummaryAgentOutputSchema(
            summary=raw_summary,
            status="completed",
            messages=_messages + [{"role": "assistant", "content": raw_summary}],
        )

    # --- Prompt to refine & format the raw content ---
    if use_llm:
        try:
            # lazy imports so tests can run without langchain installed
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            from langchain_openai import ChatOpenAI

            summary_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a friendly and professional trip planning assistant. 
                Refine the provided raw trip summary into a clear, well-structured Markdown document. 
                Use headings, bullet points, and a conversational tone.
                Always try to cap the summary at around 600 words. 
                Make it engaging and easy to read, as if explaining the trip plan to a friend. 
                Ensure the summary is factually accurate based on the provided details. 
                If any details are missing or unclear, make reasonable assumptions to fill in the gaps, 
                but do not fabricate information. 
                Do NOT invent new facts. Only reformat and polish the given information. 
                Do NOT share private info. Do NOT share harmful info."""),
                ("human", "Here is the raw trip summary:\n{raw_info}")
            ])

            # create llm lazily
            llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.3, max_tokens=800)
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
    else:
        # LLM disabled (tests/offline): return the raw summary
        return SummaryAgentOutputSchema(
            summary=raw_summary,
            status="completed",
            messages=_messages + [{"role": "assistant", "content": raw_summary}],
        )
