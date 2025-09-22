from langgraph.graph import StateGraph, END

from server.agents.location_agent.location_agent import run_location_agent
from server.agents.orchestrator_agent.orchestrator_agent import call_orchestrator_agent
from server.agents.summary_agent.summary_agent import generate_summary
from server.schemas.global_schema import TravelState
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema
from server.schemas.summary_schemas import SummaryAgentInputSchema


# # --- Wrapper: Orchestrator ---
# def orchestrator_node(state: TravelState) -> dict:
#     response = call_orchestrator_agent(
#         OrchestratorAgent4InputSchema(query=state.additional_info or state.messages[-1]["content"] if state.messages else "")
#     )
#     return {**state.dict(), **response}
#
# # --- Wrapper: Location Agent ---
# def location_node(state: TravelState) -> dict:
#     response = run_location_agent(state)
#     locations = [loc["name"] for loc in response.get("recommended_locations", [])]
#     return {**state.dict(), "locations_to_visit": locations}
#
# # --- Wrapper: Summary Agent ---
# def summary_node(state: TravelState) -> dict:
#     response = generate_summary(SummaryAgentInputSchema(**state.dict()))
#     return {**state.dict(), "summary": response.summary}
#

def orchestrator_node(state: TravelState) -> TravelState:
    response = call_orchestrator_agent(
        OrchestratorAgent4InputSchema(query=state.additional_info)
    )
    # Update TravelState with the LLM response
    return TravelState(**{**state.dict(), **response})

def location_node(state: TravelState) -> TravelState:
    response = run_location_agent(state)
    locations = [loc["name"] for loc in response.get("recommended_locations", [])]
    return TravelState(**{**state.dict(), "locations_to_visit": locations})

def summary_node(state: TravelState) -> TravelState:
    response = generate_summary(SummaryAgentInputSchema(**state.dict()))
    return TravelState(**{**state.dict(), "summary": response.summary})


def build_graph():
    graph = StateGraph(TravelState)

    # --- Register nodes ---
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("location", location_node)
    graph.add_node("summary", summary_node)

    # --- Entry point ---
    graph.set_entry_point("orchestrator")

    # --- Branching logic with retries ---
    def orchestrator_router(state: TravelState) -> str:
        mandatory = ["destination", "start_date", "end_date", "no_of_traveler", "type_of_trip"]
        missing = [f for f in mandatory if getattr(state, f) in (None, "", [], 0)]

        if missing:
            if state.retry_count >= 3:
                print(f"DEBUG: Max retries reached ({state.retry_count}), forcing flow to location.")
                return "location"
            else:
                state.retry_count += 1
                print(f"DEBUG: Missing fields {missing}, retry {state.retry_count} → looping back.")
                return "orchestrator"
        else:
            print("DEBUG: All mandatory fields filled, proceeding to location.")
            return "location"

    graph.add_conditional_edges(
        "orchestrator",
        orchestrator_router,
        {
            "orchestrator": "orchestrator",  # loop until retries exhausted
            "location": "location"
        }
    )

    # Normal linear flow
    graph.add_edge("location", "summary")
    graph.add_edge("summary", END)

    return graph.compile()
