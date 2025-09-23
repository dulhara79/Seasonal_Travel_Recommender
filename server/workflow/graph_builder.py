# python
from pydantic import ValidationError
from langgraph.graph import StateGraph, END

from server.agents.activity_agent.activity_indexer import suggest_activities
from server.agents.location_agent.location_agent import run_location_agent
from server.agents.orchestrator_agent.orchestrator_agent import call_orchestrator_agent
from server.agents.summary_agent.summary_agent import generate_summary
from server.agents.followup_agent.followup_agent import FollowUpAgent

from server.schemas.global_schema import TravelState
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema
from server.schemas.summary_schemas import SummaryAgentInputSchema

# Mandatory fields and friendly follow-up questions
MANDATORY_FIELDS = ["destination", "start_date", "end_date", "no_of_traveler", "type_of_trip"]
FOLLOWUP_QUESTIONS = {
    "destination": "🌍 Where would you like to travel?",
    "start_date": "📅 What is your trip start date? (YYYY-MM-DD)",
    "end_date": "📅 What is your trip end date? (YYYY-MM-DD)",
    "no_of_traveler": "👥 How many people are traveling?",
    "type_of_trip": "🎯 What type of trip is this (leisure, adventure, business, family)?",
    "budget": "💰 What is your budget (low, medium, high)?",
    "user_preferences": "✨ Any preferences? (e.g., beach, culture, food) — comma separated"
}

# Initialize followup agent with templates and mandatory field list
followup_agent = FollowUpAgent(question_templates=FOLLOWUP_QUESTIONS, mandatory_fields=MANDATORY_FIELDS)

# --- Node Implementations ---

def orchestrator_node(state: TravelState) -> TravelState:
    """Extract structured info from user query using the orchestrator agent."""
    orchestrator_inputs = {
        "query": state.additional_info or (state.messages[-1]["content"] if state.messages else "")
    }

    response = call_orchestrator_agent(OrchestratorAgent4InputSchema(**orchestrator_inputs))

    # Merge the response with current state
    updated_state = {**state.dict(), **response}
    return TravelState(**updated_state)


def followup_node(state: TravelState) -> TravelState:
    """Ask creative follow-up questions for missing fields and merge any provided answers."""
    previous_answers = getattr(state, "followup_answers", {}) or {}
    fields, missing_questions = followup_agent.collect(
        additional_info=state.additional_info or "",
        followup_answers=previous_answers
    )

    # Merge any newly filled fields into state dict
    updated = {**state.dict(), **fields}
    # Store the questions to allow UI/consumer to ask the user
    updated["missing_questions"] = missing_questions
    # Keep the followup_answers so callers can populate them in the next iteration
    updated["followup_answers"] = previous_answers

    print(f"DEBUG: FollowUpAgent filled fields={fields}, still missing={list(missing_questions.keys())}")

    return TravelState(**updated)


def location_node(state: TravelState) -> TravelState:
    """Recommend locations based on extracted query."""
    response = run_location_agent(state)
    locations = [loc["name"] for loc in response.get("recommended_locations", [])]
    return TravelState(**{**state.dict(), "locations_to_visit": locations})


def activity_node(state: TravelState) -> TravelState:
    """Suggest activities for the selected locations."""
    response = suggest_activities(state)
    day_plans = response.get("day_plans", [])
    return TravelState(**{**state.dict(), "activities": day_plans})

def summary_node(state: TravelState) -> TravelState:
    """Generate final structured summary for the trip plan with input sanitization."""
    # Build a mutable copy of the state dict
    data = state.dict().copy()

    # Ensure known optional string fields are not None (avoid pydantic string_type errors)
    for k in ("budget", "destination", "start_date", "end_date", "type_of_trip", "additional_info"):
        if data.get(k) is None:
            data[k] = ""

    # Try creating the schema; on validation error, coerce remaining None -> safe defaults
    try:
        response = generate_summary(SummaryAgentInputSchema(**data))
    except ValidationError:
        for k, v in list(data.items()):
            if v is None:
                # Coerce None to reasonable defaults: empty string for scalars, empty list for lists
                data[k] = "" if not isinstance(v, list) else []
        response = generate_summary(SummaryAgentInputSchema(**data))

    return TravelState(**{**state.dict(), "summary": response.summary})


# --- Router for Orchestrator ---
def orchestrator_router(state: TravelState) -> str:
    missing = [f for f in MANDATORY_FIELDS if getattr(state, f) in (None, "", [], 0)]

    if missing:
        print(f"DEBUG: Missing fields {missing} → routing to followup.")
        return "followup"
    else:
        print("DEBUG: All mandatory fields filled → routing to location.")
        return "location"


# --- Enhanced Router for Followup ---
def followup_router(state: TravelState) -> str:
    """Determine if we need to continue asking follow-up questions."""
    missing = [f for f in MANDATORY_FIELDS if getattr(state, f) in (None, "", [], 0)]

    # If there are still missing fields and the agent produced questions, keep asking
    if missing and getattr(state, "missing_questions", {}):
        print(f"DEBUG: Still missing fields {missing} → continuing followup.")
        return "followup"
    else:
        print("DEBUG: Followup complete or no missing questions → routing to orchestrator.")
        return "orchestrator"


# --- Graph Builder ---
def build_graph():
    graph = StateGraph(TravelState)

    # Register nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("followup", followup_node)
    graph.add_node("location", location_node)
    graph.add_node("activity", activity_node)
    graph.add_node("summary", summary_node)

    # Entry point
    graph.set_entry_point("orchestrator")

    # Routing from orchestrator
    graph.add_conditional_edges(
        "orchestrator",
        orchestrator_router,
        {
            "followup": "followup",
            "location": "location",
        }
    )

    # Routing from followup - conditionally loop back to orchestrator or continue followup
    graph.add_conditional_edges(
        "followup",
        followup_router,
        {
            "followup": "followup",  # Continue asking questions
            "orchestrator": "orchestrator",  # All questions answered, go back to orchestrator
        }
    )

    # Normal flow
    graph.add_edge("location", "activity")
    graph.add_edge("activity", "summary")
    graph.add_edge("summary", END)

    return graph.compile()