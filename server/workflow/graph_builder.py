from langgraph.graph import StateGraph, END

from server.agents.location_agent.location_agent import run_location_agent
from server.agents.orchestrator_agent.orchestrator_agent import call_orchestrator_agent
from server.agents.summary_agent.summary_agent import generate_summary
from server.schemas.global_schema import TravelState
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema
from server.schemas.summary_schemas import SummaryAgentInputSchema


# --- Wrapper: Orchestrator ---
def orchestrator_node(state: TravelState) -> dict:
    response = call_orchestrator_agent(
        OrchestratorAgent4InputSchema(query=state.additional_info or state.messages[-1]["content"] if state.messages else "")
    )
    return {**state.dict(), **response}

# --- Wrapper: Location Agent ---
def location_node(state: TravelState) -> dict:
    response = run_location_agent(state)
    locations = [loc["name"] for loc in response.get("recommended_locations", [])]
    return {**state.dict(), "locations_to_visit": locations}

# --- Wrapper: Summary Agent ---
def summary_node(state: TravelState) -> dict:
    response = generate_summary(SummaryAgentInputSchema(**state.dict()))
    return {**state.dict(), "summary": response.summary}

def build_graph():
    graph = StateGraph(TravelState)

    # Register nodes
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("location", location_node)
    graph.add_node("summary", summary_node)

    # Define execution order
    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", "location")
    graph.add_edge("location", "summary")
    graph.add_edge("summary", END)

    return graph.compile()
