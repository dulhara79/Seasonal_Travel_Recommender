from langgraph.graph import StateGraph, END

from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema, OrchestratorAgent4OutpuSchema
from server.agents.orchestrator_agent.orchestrator_agent import call_orchestrator_agent
from server.agents.activity_agent_1.activity_agent import suggest_activities
from server.agents.summary_agent.summary_agent import generate_summary

def build_graph():
    workflow = StateGraph(OrchestratorAgent4InputSchema)

    workflow.add_node("orchestrator_agent", call_orchestrator_agent)
    workflow.add_node("activity_agent", suggest_activities)
    workflow.add_node("summary_agent", generate_summary)

    workflow.set_entry_point("orchestrator_agent")

    workflow.add_edge("orchestrator_agent", "activity_agent")
    workflow.add_edge("activity_agent", "summary_agent")
    workflow.add_edge("summary_agent", END)

    app= workflow.compile()

    return app
