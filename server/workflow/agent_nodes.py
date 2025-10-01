# agent_nodes.py

from typing import Dict, Any, List, Optional
import json

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
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema


# from server.schemas.location_agent_schemas import LocationAgentOutputSchema # Already in state
# Placeholder for missing agents
def _run_activity_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print("Executing Activity Agent: Generating activity plans...")
    # --- Actual Agent Logic ---
    # activity_output = run_activity_agent(state['trip_data'], state['location_recs'])
    # state['activity_recs'] = activity_output
    # state['final_response'] = "Generated some great activity suggestions!"
    # --- Placeholder Logic ---
    state['activity_recs'] = {"day_plans": [
        {"date": "2026-07-16", "suggestions": [{"title": "Visit Sigiriya Rock", "time_of_day": "morning"}]}]}
    state['final_response'] = "Activity plans have been generated."
    return state


def _run_packing_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    print("Executing Packing Agent: Generating packing list...")
    # --- Actual Agent Logic ---
    # packing_output = run_packing_agent(state['trip_data'])
    # state['packing_recs'] = packing_output
    # --- Placeholder Logic ---
    state['packing_recs'] = {"categories": [
        {"name": "Essentials", "items": [{"name": "Sunscreen", "reason": "High UV index in Sri Lanka"}]}]}
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
    if state.get("latest_summary") and (any(k in query for k in style_keywords) or any(k in query for k in modify_keywords)):
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

    # FIX 2: Remove the unnecessary conversion/error-prone line.
    # The existing trip_data is not passed as 'prev_data' in the provided call_orchestrator_agent
    # The call_orchestrator_agent function you provided in the prompt takes the state and user_responses.
    # It does not take prev_response_pydantic as an argument in its signature in your provided code block:
    # def call_orchestrator_agent(state: OrchestratorAgent4InputSchema, user_responses: list = None):

    # If you need to pass the *current* state of the trip data, you must adjust the call:
    # We will assume for now that the orchestrator is designed to start fresh with the new query
    # and merge with the current state *internally* (which it did in the provided code).

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
    state['final_response'] = f"Location recommendations generated for {trip_data_for_location.get('destination')}."
    return state


# === 5. Summary Node ===
def summary_node(state: TripPlanState) -> Dict[str, Any]:
    """Aggregates all results and generates the final user-facing summary."""
    print("--- NODE: Summary Agent Executing...")

    # Combine all structured data into a single dict for the Summary Agent Input Schema
    summary_input = {
        **state['trip_data'].dict(),
        "location_recommendations": state['location_recs'],
        "activity_recommendations": state['activity_recs'],
        "packing_list": state['packing_recs'],  # Assuming packing_recs is structured
        "status": "completed"
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
    # Runs the location agent as a single step and returns control
    state = location_node(state)  # Reuse the location logic
    state[
        'final_response'] = f"Here are some location ideas based on your query:\n\n{json.dumps(state['location_recs'], indent=2)}"
    return state


def simple_activity_node(state: TripPlanState) -> Dict[str, Any]:
    # Placeholder for running a single activity agent call
    state = _run_activity_agent(state)
    state['final_response'] = "Here are some activity ideas..."  # Update this to pull actual recs
    return state


def simple_packing_node(state: TripPlanState) -> Dict[str, Any]:
    # Placeholder for running a single packing agent call
    state = _run_packing_agent(state)
    state['final_response'] = "Here is a packing list..."  # Update this to pull actual recs
    return state
