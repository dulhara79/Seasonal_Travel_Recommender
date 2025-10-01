# agent_nodes.py

from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timedelta

# --- LangGraph/State Imports ---
from langgraph.graph import StateGraph
from server.workflow.app_state import TripPlanState

# --- Agent Imports (Assuming your files are accessible) ---
# NOTE: Replace these with your actual import paths
from server.agents.decision_agent.decision_agent import decision_agent_node as _run_decision_agent
from server.agents.chat_agent.chat_agent import chat_agent_node as _run_chat_agent
from server.agents.orchestrator_agent.orchestrator_agent import call_orchestrator_agent
from server.agents.location_agent.location_agent import run_location_agent as _run_location_agent
from server.agents.summary_agent.summary_agent import generate_summary as _run_summary_agent
from server.agents.summary_agent.summary_refiner import refine_summary as _run_summary_refiner
from server.agents.activity_agent.activity_indexer import suggest_activities
from server.agents.packing_agent.packing_agent import generate_packing_list
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema


# --- Utility Functions to Format Structured Agent Outputs ---

def format_packing_list(packing_data: Dict[str, Any]) -> str:
    """
    Converts the structured packing list dictionary into a readable Markdown string.
    """
    if not packing_data or not packing_data.get('categories'):
        return "Sorry, I could not generate a packing list at this time."

    packing_text = ["### 🎒 Suggested Packing List\n"]

    for category in packing_data['categories']:
        name = category.get('name', 'General Items')
        items = category.get('items', [])

        packing_text.append(f"**{name}:**")
        if not items:
            packing_text.append("- No items suggested.")
            continue

        for item in items:
            item_name = item.get('name', 'Unknown Item')
            reason = item.get('reason')

            if reason:
                # Use a slightly cleaner format for reasons
                packing_text.append(f"- {item_name} *({reason})*")
            else:
                packing_text.append(f"- {item_name}")
        packing_text.append("")  # Spacer

    if packing_data.get('notes'):
        notes = " ".join(packing_data['notes']) if isinstance(packing_data['notes'], list) else packing_data['notes']
        if notes.strip():
            packing_text.append("---\n")
            packing_text.append(f"**Notes:** {notes.strip()}")

    return "\n".join(packing_text).strip()


def format_activity_list(activity_data: Dict[str, Any]) -> str:
    """
    Converts the structured Activity Agent JSON into a clean, markdown-friendly string.
    """
    if not activity_data or not activity_data.get('day_plans'):
        return "I could not generate a detailed activity plan based on the available data."

    destination = activity_data.get("destination", "Your Destination")
    theme = activity_data.get("overall_theme", "General Exploration")

    summary_parts = []
    summary_parts.append(f"### 🎉 Activities for {destination}\n")
    summary_parts.append(f"**Theme:** {theme}\n")
    summary_parts.append("---\n")

    for day in activity_data.get('day_plans', []):
        date_str = day.get("date", "Unknown Date")
        summary_parts.append(f"#### 🗓️ {date_str}\n")

        suggestions = day.get("suggestions", [])
        for suggestion in suggestions:
            time = suggestion.get("time_of_day", "Time Unknown").capitalize()
            title = suggestion.get("title", "Activity")
            why = suggestion.get("why", "Explore the area.")
            price = suggestion.get("price_level", "Medium").capitalize()

            # Format each suggestion clearly
            summary_parts.append(f"- **{time}** ({price} Budget): **{title}**")
            summary_parts.append(f"  > *Why:* {why}")

            # Add weather risk and alternatives if present
            if suggestion.get("weather_risk") and suggestion.get("alternatives"):
                alts = ", ".join(suggestion['alternatives'])
                summary_parts.append(
                    f"  > ⚠️ **Risk Alert:** Consider these alternatives due to potential weather: {alts}")

        summary_parts.append("\n")  # Add space after each day

    notes = activity_data.get('notes')
    if notes:
        summary_parts.append("---\n")
        summary_parts.append("### 📝 Notes from Planner\n")
        summary_parts.append(f"{notes}\n")

    return "\n".join(summary_parts)


# === Internal Agent Runner Nodes ===

def _run_activity_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print("Executing Activity Agent: Generating activity plans...")
    # The suggest_activities function likely expects a dict of the trip details
    trip_data_for_activity = state['trip_data'].dict() if state.get('trip_data') else {}
    # --- Actual Agent Logic ---
    activity_output = suggest_activities(trip_data_for_activity)
    state['activity_recs'] = activity_output
    # Mirror naming convention to be robust for downstream consumers
    state['activity_recommendations'] = state['activity_recs']
    state['final_response'] = "Activity plans have been generated."
    return state


def _run_packing_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print("Executing Packing Agent: Generating packing list...")
    # The generate_packing_list function expects a dict of the trip details
    trip_data_for_packing = state['trip_data'].dict() if state.get('trip_data') else {}

    # Extract existing activity recs if available, or pass an empty list
    activity_titles = []
    activity_recs = state.get('activity_recs')
    if activity_recs and activity_recs.get('day_plans'):
        for day in activity_recs['day_plans']:
            for suggestion in day.get('suggestions', []):
                activity_titles.append(suggestion.get('title'))

    # --- Actual Agent Logic ---
    # The generate_packing_list function returns a DICT now
    packing_output = generate_packing_list(trip_data_for_packing, suggested_activities=activity_titles)

    # Heuristic: if the LLM-produced packing output looks sparse (e.g., very few categories
    # or categories with very few items), prefer deterministic fallback to ensure useful results.
    try:
        cats = packing_output.get("categories") if isinstance(packing_output, dict) else None
        total_items = sum(len(c.get("items", [])) for c in cats) if cats else 0
        if not cats or total_items <= 1:
            # Re-generate using deterministic rules (no LLM) for more robust coverage
            packing_output = generate_packing_list(trip_data_for_packing, suggested_activities=activity_titles, use_llm=False)
    except Exception:
        # If any error occurs during the heuristic, just proceed with original packing_output
        pass

    state['packing_recs'] = packing_output
    # Mirror naming convention so the Summary node can read either key
    state['packing_list'] = state['packing_recs']
    state['final_response'] = "Packing list is ready!"
    return state


# === 1. Router/Decision Node ===
def route_user_query(state: TripPlanState) -> Dict[str, Any]:
    """
    Invokes the Decision Agent, determines the next action, and returns the
    updates as a dictionary, including the 'intent'.
    """
    print(f"--- ROUTER: Classifying user intent for: {state['user_query'][:50]}...")

    state_dict = dict(state)
    updated_state = _run_decision_agent(state_dict)

    # 1. Determine the raw intent from the LLM
    raw_intent = updated_state.get("intent", "chat_agent")

    # If the current state already contains partial trip_data awaiting input,
    # force the orchestrator path so the user's reply resumes the collection flow.
    trip_data = state.get('trip_data')
    if trip_data:
        # trip_data may be a Pydantic object or a dict
        if hasattr(trip_data, 'model_dump'):
            td = trip_data.model_dump()
        else:
            td = trip_data

        if isinstance(td, dict) and td.get('status') == 'awaiting_user_input':
            return {"intent": "orchestrator_agent"}

    # 2. Check for the Refinement case FIRST (as your heuristic)
    query = state['user_query'].lower()
    style_keywords = ["shorter", "longer", "tone", "funnier", "adventurous", "polish", "style"]

    # New: catch explicit user requests to change or remove parts of the plan
    modify_keywords = [
        "change the plan",
        "change my plan",
        "don't like",
        "dont like",
        "don't want",
        "dont want",
        "remove",
        "no hiking",
        "avoid hiking",
        "don't hike",
        "dont hike",
        "don't like hiking",
        "dont like hiking",
        "no hikes",
        "no hiking",
        "skip hiking",
    ]

    # If we have a previous summary and the user asks to modify the plan,
    # prefer the refiner path so we update the existing plan instead of
    # restarting extraction which may re-ask missing fields.
    if state.get("latest_summary") and (
            any(k in query for k in style_keywords) or any(k in query for k in modify_keywords)):
        determined_intent = "refine_summary"
    else:
        determined_intent = raw_intent

    # 3. CRITICAL FIX: Return a dictionary containing the intent
    return {"intent": determined_intent}


# === 2. Chat Node ===
def chat_node(state: TripPlanState) -> Dict[str, Any]:
    """Handles general conversational flow."""
    print("--- NODE: Chat Agent Executing...")
    state_dict = dict(state)
    updated_state = _run_chat_agent(state_dict)  # The original chat_agent_node updates chat_history and final_summary

    # Map the chat agent's output back to the final_response key
    state['final_response'] = updated_state.get('final_summary')
    state['chat_history'] = updated_state.get('chat_history', [])
    return state


# === 3. Orchestrator Node (The Data Gatherer) ===
def orchestrator_node(state: TripPlanState) -> Dict[str, Any]:
    """Manages the full planning process, running the extraction and Q&A loop."""
    print("--- NODE: Orchestrator Agent Executing...")

    # 1. Prepare input schema for the orchestrator function
    orchestrator_input = OrchestratorAgent4InputSchema(
        query=state['user_query']
    )

    # Determine if we're resuming a previously awaiting orchestrator state.
    prev_trip_data = None
    if state.get('trip_data'):
        td = state['trip_data']
        if hasattr(td, 'model_dump'):
            prev_trip_data = td.model_dump()
        elif isinstance(td, dict):
            prev_trip_data = td

    # If previous trip_data indicates we were awaiting user input, resume the
    # orchestrator by passing the user's current message as the answer and the
    # previous partial state so the orchestrator can continue asking until
    # all mandatory fields are collected.
    if prev_trip_data and prev_trip_data.get('status') == 'awaiting_user_input':
        user_answer = state.get('user_query')
        print(f"DEBUG: Resuming orchestrator with user answer: {user_answer}")
        final_data_pydantic = call_orchestrator_agent(
            orchestrator_input,
            user_responses=[user_answer],
            prev_json_response=prev_trip_data
        )
    else:
        # Normal fresh invocation
        final_data_pydantic = call_orchestrator_agent(orchestrator_input, user_responses=[])

    # Update State. Convert the returned Pydantic object to a dictionary for LangGraph's TypedDict state update.
    # The orchestrator agent returns a Pydantic object (OrchestratorAgent4OutpuSchema).
    # We store the Pydantic object itself in the state to maintain type integrity.
    state['trip_data'] = final_data_pydantic

    # Conditional: Decide if we continue planning or ask a follow-up question
    # Now that trip_data is a Pydantic object, use .model_dump() to check status.
    final_data_dict = final_data_pydantic.model_dump()

    if final_data_dict.get('status') == 'complete':
        return state  # Continue to Location Agent
    else:
        # The orchestrator should have set a message detailing the missing info
        if final_data_dict.get('messages'):
            last_msg = final_data_dict['messages'][-1]
            # Support message formats produced by the orchestrator agent
            question = None
            if isinstance(last_msg, dict):
                # New structured format uses the 'question' key
                question = last_msg.get('question') or last_msg.get('content')
            else:
                # Fallback to raw string messages
                question = str(last_msg)

            state['final_response'] = question or "What else can I help you plan?"
        else:
            state['final_response'] = "What else can I help you plan?"

        # The Orchestrator's job is complete for this turn; it awaits user input.
        return state


# === 4. Location Node ===
def location_node(state: TripPlanState) -> Dict[str, Any]:
    """Generates structured location recommendations."""
    print("--- NODE: Location Agent Executing...")

    # The Location Agent expects a dict/pydantic of the trip details
    trip_data_for_location = state['trip_data'].dict() if state['trip_data'] else {}

    location_output = _run_location_agent(trip_data_for_location)
    state['location_recs'] = location_output  # LocationAgentOutputSchema.parse_obj(location_output)
    # Mirror naming convention to support summary agent expectations
    state['location_recommendations'] = state['location_recs']
    state['final_response'] = f"Location recommendations generated for {trip_data_for_location.get('destination')}."
    return state


# === 5. Summary Node ===
def summary_node(state: TripPlanState) -> Dict[str, Any]:
    """Aggregates all results and generates the final user-facing summary."""
    print("--- NODE: Summary Agent Executing...")

    # Combine all structured data into a single dict for the Summary Agent Input Schema
    # Use .get with sensible fallbacks so standalone agent outputs or differently
    # named keys don't cause KeyError and are still picked up by the summary.
    trip_data_dict = state['trip_data'].dict() if state.get('trip_data') else {}

    summary_input = {
        **trip_data_dict,
        "location_recommendations": state.get('location_recs') or state.get('location_recommendations') or {},
        "activity_recommendations": state.get('activity_recs') or state.get('activity_recommendations') or {},
        "packing_list": state.get('packing_recs') or state.get('packing_list') or {},
        "status": "completed",
    }

    summary_output_pydantic = _run_summary_agent(summary_input, use_llm=True)

    state['latest_summary'] = summary_output_pydantic.summary
    state['final_response'] = summary_output_pydantic.summary  # Show the summary to the user
    return state


# === 6. Refiner Node ===
def refiner_node(state: TripPlanState) -> Dict[str, Any]:
    """Refines the existing summary text based on user feedback."""
    print("--- NODE: Summary Refiner Executing...")

    previous_summary = state['latest_summary']
    user_feedback = state['user_query']

    new_summary = _run_summary_refiner(previous_summary, user_feedback)

    state['latest_summary'] = new_summary
    state['final_response'] = new_summary  # Show the refined summary to the user
    return state


# === 7. Simple Agent Nodes (Location/Activity/Packing) ===
def simple_location_node(state: TripPlanState) -> Dict[str, Any]:
    """Runs the Location Agent and formats the raw JSON for a direct user response."""
    # Runs the location agent as a single step and returns control
    state = location_node(state)  # Reuse the location logic
    # Use json.dumps for the raw location recs since we don't have a simple formatter defined for this output
    state[
        'final_response'] = f"Here are some location ideas based on your query:\n\n{json.dumps(state['location_recs'], indent=2)}"
    return state


def simple_activity_node(state: TripPlanState) -> Dict[str, Any]:
    """Runs the Activity Agent and formats the structured result for a direct user response."""
    # Runs the activity agent as a single step and returns control
    state = _run_activity_agent(state)

    # CRITICAL FIX: Use the utility function to format the structured activity plan
    activity_data = state.get('activity_recs') or state.get('activity_recommendations')
    formatted_plan = format_activity_list(activity_data)

    # The final response is now the readable Markdown plan
    state['final_response'] = formatted_plan
    return state


def simple_packing_node(state: TripPlanState) -> Dict[str, Any]:
    """Runs the Packing Agent and formats the structured result for a direct user response."""
    # Runs the packing agent as a single step and returns control
    state = _run_packing_agent(state)

    # CRITICAL FIX: Use the utility function to format the structured packing list
    packing_data = state.get('packing_recs') or state.get('packing_list')
    formatted_list = format_packing_list(packing_data)

    # The final response is now the readable Markdown list
    state['final_response'] = formatted_list
    return state
