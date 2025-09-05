import datetime
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from server.utils.config import OPENAI_API_KEY, LLM_MODEL
from server.schemas.summary_schemas import SummaryAgentInputSchema, SummaryAgentOutputSchema

# Load LLM
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=LLM_MODEL, temperature=0.3, max_tokens=800)


def generate_summary(state: SummaryAgentInputSchema) -> SummaryAgentOutputSchema:
    """
    Generates a refined, conversational summary of the trip
    using the collected information in SummaryAgentInputSchema.
    """

    print(f"Generating summary for state: {state}")

    # --- Build raw summary parts ---
    response_parts = []

    if state.destination:
        response_parts.append(f"# ✈️ Trip Summary for {state.destination}\n")

    if state.start_date and state.end_date:
        try:
            start_dt = datetime.datetime.strptime(state.start_date, "%Y-%m-%d").strftime("%B %d, %Y")
            end_dt = datetime.datetime.strptime(state.end_date, "%Y-%m-%d").strftime("%B %d, %Y")
            response_parts.append(f"## 🗓️ Dates\n- From **{start_dt}** to **{end_dt}**\n")
        except ValueError:
            response_parts.append(f"## 🗓️ Dates\n- {state.start_date} → {state.end_date} (format issue)\n")

    if state.no_of_traveler:
        traveler_text = "solo" if state.no_of_traveler == 1 else f"{state.no_of_traveler} travelers"
        response_parts.append(f"## 👥 Travelers\n- This trip is planned for **{traveler_text}**\n")

    if state.budget:
        response_parts.append(f"## 💰 Budget\n- Budget level: **{state.budget.capitalize()}**\n")

    if state.user_preferences:
        prefs = ", ".join(state.user_preferences)
        response_parts.append(f"## 🎯 Preferences\n- Your main interests: **{prefs}**\n")

    if state.type_of_trip:
        response_parts.append(f"## 🌍 Trip Type\n- You described this as a **{state.type_of_trip}** trip.\n")

    if state.locations_to_visit:
        response_parts.append("## 🗺️ Locations to Visit")
        for loc in state.locations_to_visit:
            response_parts.append(f"- {loc}")
        response_parts.append("")

    if state.activities:
        response_parts.append("## 🎡 Activities")
        for act in state.activities:
            response_parts.append(f"- {act}")
        response_parts.append("")

    if state.packing_list:
        response_parts.append("## 🎒 Suggested Packing List")
        for item in state.packing_list:
            response_parts.append(f"- {item}")
        response_parts.append("")

    if state.additional_info:
        response_parts.append("## ℹ️ Additional Info")
        response_parts.append(f"{state.additional_info}\n")

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
            messages=state.messages + [{"role": "assistant", "content": final_summary}]
        )
    except Exception as e:
        fallback_msg = f"⚠️ I encountered an error creating the polished summary: {e}. Here’s the raw summary instead:\n\n{raw_summary}"
        return SummaryAgentOutputSchema(
            summary=fallback_msg,
            status="error",
            messages=state.messages + [{"role": "assistant", "content": fallback_msg}]
        )
