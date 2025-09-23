import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from server.schemas.summary_schemas import SummaryAgentInputSchema, SummaryAgentOutputSchema

# Load LLM
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.3, max_tokens=800)


def generate_summary(state: SummaryAgentInputSchema | dict) -> SummaryAgentOutputSchema:
    """
    Generates a refined, conversational summary of the trip
    using the collected information in SummaryAgentInputSchema.
    """

    print(f"Generating summary for state: {state}")

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
    else:
        _dst = state.destination
        _start = state.start_date
        _end = state.end_date
        _num = state.no_of_traveler
        _budget = state.budget
        _prefs = state.user_preferences
        _type = state.type_of_trip
        _locations = state.locations_to_visit
        _activities = state.activities
        _packing = state.packing_list
        _additional = state.additional_info
        _messages = state.messages

    # --- Build raw summary parts ---
    response_parts = []

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

    if _locations:
        response_parts.append("## 🗺️ Locations to Visit")
        for loc in _locations:
            response_parts.append(f"- {loc}")
        response_parts.append("")

    if _activities:
        response_parts.append("## 🎡 Activities")
        for act in _activities:
            response_parts.append(f"- {act}")
        response_parts.append("")

    if _packing:
        response_parts.append("## 🎒 Suggested Packing List")
        for item in _packing:
            response_parts.append(f"- {item}")
        response_parts.append("")

    if _additional:
        response_parts.append("## ℹ️ Additional Info")
        response_parts.append(f"{_additional}\n")

    raw_summary = "\n".join(response_parts)

    # --- Prompt to refine & format the raw content ---
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

    summary_chain = summary_prompt | llm | StrOutputParser()

    try:
        final_summary = summary_chain.invoke({"raw_info": raw_summary})

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
