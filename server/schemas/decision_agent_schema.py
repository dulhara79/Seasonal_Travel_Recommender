from pydantic import BaseModel, Field


class AgentRouteDecision(BaseModel):
    """
        Schema for the Decision Agent's output, determining the next agent in the graph.
    """
    next_agent: str = Field(
        description="The name of the next agent to route the query to. Must be one of: 'chat_agent', 'orchestrator_agent', 'location_agent', 'activity_agent', 'packing_agent'."
    )
