# app_state.py

from typing import TypedDict, List, Tuple, Optional, Any, Dict
from server.schemas.orchestrator_schemas import OrchestratorAgent4OutpuSchema
from server.schemas.location_agent_schemas import LocationAgentOutputSchema


# Assuming you have schemas for Activity and Packing:
# from server.schemas.activity_schemas import ActivityAgentOutputSchema
# from server.schemas.packing_schemas import PackingOutput
# We'll use a generic Dict[str, Any] for now as the exact schemas weren't provided.
from server.agents.packing_agent.packing_agent import PackingOutput


class TripPlanState(TypedDict):
    """
    The central state object passed between all LangGraph nodes.
    It contains the user's input, the evolving trip data, and the final response.
    """
    # === Conversation State ===
    user_query: str  # The latest query from the user
    chat_history: List[Tuple[str, str]]  # History of the conversation: (role, content)

    # === Routing State ===
    intent: Optional[str]  # Determined by the Decision Agent (e.g., 'orchestrator_agent')

    # === Planning Data (Structured Schemas) ===
    # This stores the mandatory, validated planning data
    trip_data: Optional[OrchestratorAgent4OutpuSchema]

    # === Recommendation Data (Structured Schemas) ===
    location_recs: Optional[LocationAgentOutputSchema]  # Output from Location Agent
    activity_recs: Optional[Dict[str, Any]]  # Output from Activity Agent (Placeholder)
    packing_recs: Optional[Dict[str, Any]]  # Output from Packing Agent (Placeholder)

    # === Final Output State ===
    latest_summary: Optional[str]  # The final, polished Markdown summary text
    final_response: Optional[str]  # The text response to be returned to the user immediately
