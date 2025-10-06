# server/api/route.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import traceback
from pydantic import ValidationError  # Added to catch schema errors

# Internal dependencies
from server.api.auth import get_current_user
from server.workflow.workflow import build_trip_workflow
from server.workflow.app_state import TripPlanState
from server.schemas.orchestrator_schemas import OrchestratorAgent4OutpuSchema  # For initial state
from server.schemas.location_agent_schemas import LocationAgentOutputSchema  # For serialization check

router = APIRouter(tags=["plan"])


# --- Schemas for API Input/Output ---
class QueryRequest(BaseModel):
    """Schema for a new user query, possibly with a previous state."""
    query: str
    # The state is passed as a JSON/dict representation of the TripPlanState
    previous_state: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Schema for the API response."""
    response: str  # The final_response text
    current_state: Dict[str, Any]  # The full new state (for saving/next turn)


# --- Utility to ensure Pydantic objects are serialized for the API response ---
def _serialize_state_for_api(state: Dict[str, Any]) -> Dict[str, Any]:
    """Converts known Pydantic models in the state dict to standard dictionaries."""

    # Deep copy the state to avoid modifying the LangGraph in-memory state object
    serialized_state = state.copy()

    # Key fields that might hold Pydantic models based on TripPlanState definition
    pydantic_fields = {
        "trip_data": OrchestratorAgent4OutpuSchema,
        "location_recs": LocationAgentOutputSchema,
        # Add other structured fields here (activity_recs, packing_recs) if they use Pydantic models
    }

    for key, Model in pydantic_fields.items():
        if key in serialized_state and serialized_state[key] is not None:
            value = serialized_state[key]

            # 1. If it's the actual Pydantic object (returned by an agent node)
            if hasattr(value, 'model_dump'):
                serialized_state[key] = value.model_dump()

            # 2. If it's a dict that was successfully loaded from history, ensure it's validated
            elif isinstance(value, dict):
                try:
                    # Attempt to validate and dump it again to ensure compliance
                    validated_model = Model.model_validate(value)
                    serialized_state[key] = validated_model.model_dump()
                except (ValidationError, TypeError):
                    # If validation fails, leave it as is or log a warning
                    print(f"Warning: Could not validate stored dictionary for key: {key}")
                    pass  # Keep the original dictionary if validation fails

    return serialized_state


# --- Initialize Workflow ---
try:
    app_workflow = build_trip_workflow()
    print("[API] Trip planning workflow initialized.")
except Exception as e:
    app_workflow = None
    print(f"[API] ERROR: Could not initialize LangGraph workflow: {e}")


@router.post("/query", response_model=QueryResponse)
async def process_query(
        request: QueryRequest,
        current_user: dict = Depends(get_current_user)
):
    """
    Processes a user query by running the LangGraph workflow, which orchestrates
    data extraction, location recommendation, and summarization.
    """
    if not app_workflow:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The trip planning service is not available (workflow failed to initialize)."
        )

    user_query = request.query
    initial_state_dict = request.previous_state

    try:
        # --- 1. Prepare Initial State ---
        if initial_state_dict:
            # If coming from previous turns, use the state passed by the frontend
            current_state = initial_state_dict
        else:
            # Start a new conversation with base state
            # NOTE: Do NOT initialize `trip_data` with a Pydantic object set to
            # 'awaiting_user_input' because the router treats that as an in-progress
            # orchestrator flow and will force the orchestrator node. Use `None`
            # to indicate no prior orchestrator extraction has started.
            current_state: TripPlanState = {
                "user_query": user_query,
                "chat_history": [],
                "intent": None,
                "trip_data": None,
                "location_recs": None,
                "activity_recs": None,
                "packing_recs": None,
                "latest_summary": None,
                "final_response": None,
                "conversation_id": None  # Initialize ID for persistence tracking
            }

        # Ensure the current query is set correctly
        current_state['user_query'] = user_query

        # Append human query to chat history
        # NOTE: We append here to include in the LLM context, but the final history update 
        # is handled after the loop to ensure the "ai" response is paired.

        # --- 2. Execute Workflow ---
        final_state = current_state
        # Run the LangGraph
        for step_output in app_workflow.stream(current_state):
            # Update the state with the node's output
            last_node = list(step_output.keys())[-1]
            final_state.update(step_output[last_node])

            # Record lightweight processing metadata
            try:
                final_state.setdefault("_processing_steps", [])
                final_state["_processing_steps"].append({
                    "node": last_node,
                    "timestamp": datetime.utcnow().isoformat(),
                    "note": f"Completed node {last_node}",
                })
                final_state["_processing_last_node"] = last_node
            except Exception:
                pass

        # Add the final AI response to history
        # We must add the user query to the history *before* the loop 
        # or it will be missed by the next turn, but let's keep it simple
        # and ensure the UI/History component handles the turn-based history correctly.

        # --- 3. Prepare Response ---
        # Ensure all Pydantic objects are converted to dictionaries for safe JSON serialization
        response_state = _serialize_state_for_api(final_state)

        return QueryResponse(
            response=final_state.get("final_response", "I could not generate a response."),
            current_state=response_state
        )

    except Exception as e:
        print("Workflow execution error:\n", traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during planning: {e}"
        )
