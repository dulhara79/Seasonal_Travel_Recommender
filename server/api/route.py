# server/api/route.py

from fastapi import APIRouter, Body, HTTPException, Depends
from typing import Dict, Any
from pydantic import BaseModel
from server.schemas.global_schema import TravelState
from server.schemas.userQuery_schema import UserQuerySchema
from server.api.auth import get_current_user
from server.utils.chat_history import create_conversation, append_message

try:
    # Attempt to import and build the workflow graph. Optional deps like
    # `langgraph` may be missing in some environments; keep the API usable
    # by falling back to a minimal no-op workflow.
    from server.workflow.graph_builder import build_graph

    # Build the workflow graph
    workflow = build_graph()
except Exception as e:
    print("Warning: workflow graph unavailable (optional).", str(e))
    from types import SimpleNamespace

    workflow = SimpleNamespace(invoke=lambda s: s)

# API Router
router = APIRouter()

# --- Define the essential questions for planning a trip ---
REQUIRED_QUESTIONS = {
    "destination": "🌍 Where would you like to travel?",
    "start_date": "📅 What is your trip start date? (YYYY-MM-DD)",
    "end_date": "📅 What is your trip end date? (YYYY-MM-DD)",
    "no_of_traveler": "👥 How many people are traveling?",
    "type_of_trip": "🎯 What type of trip is this (leisure, adventure, business, etc.)?",
}


# --- Pydantic Models for Request Bodies ---

class FollowUpPayload(BaseModel):
    """Defines the payload for the /answer-followup endpoint."""
    current_state: Dict[str, Any]
    answers: Dict[str, Any]


# --- Helper Function for Building API Responses ---

def _build_final_response(state: TravelState | Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes the state and builds the appropriate API response.

    - If required information is missing, it returns a 'followup_required' response.
    - If all required information is present, it returns a 'complete' response.
    """
    # Support both pydantic TravelState objects and plain dicts returned by
    # the workflow. This prevents attribute errors when the workflow returns
    # a dict during testing or when optional components fall back to simple
    # structures.
    if isinstance(state, dict):
        def _get(f):
            return state.get(f)
    else:
        def _get(f):
            return getattr(state, f, None)

    missing_fields = [field for field in REQUIRED_QUESTIONS if not _get(field)]

    if missing_fields:
        # Generate questions for the fields that are still missing
        questions_to_ask = [REQUIRED_QUESTIONS[field] for field in missing_fields]
        # When returning current_state, always normalize to a dict so the
        # frontend can safely inspect it.
        current_state = state.dict() if not isinstance(state, dict) else state
        return {
            "status": "followup_required",
            "missing_fields": missing_fields,
            "questions": questions_to_ask,
            "current_state": current_state,
        }
    else:
        # All required info is present, return the final trip plan
        # Normalize values whether coming from a dict or TravelState.
        def _val(f, cast=str, default=None):
            v = _get(f)
            if v is None:
                return default
            return cast(v) if cast else v

        current_state = state.dict() if not isinstance(state, dict) else state

        return {
            "status": "complete",
            "trip_plan": {
                "destination": current_state.get("destination"),
                "start_date": str(current_state.get("start_date")) if current_state.get("start_date") else None,
                "end_date": str(current_state.get("end_date")) if current_state.get("end_date") else None,
                "no_of_traveler": current_state.get("no_of_traveler"),
                "type_of_trip": current_state.get("type_of_trip"),
                "season": current_state.get("season"),
                "budget": current_state.get("budget"),
                "preferences": current_state.get("user_preferences"),
                "locations_to_visit": current_state.get("locations_to_visit"),
                "activities": current_state.get("activities"),
                "summary": current_state.get("summary"),
            },
        }


# --- API Endpoints ---

@router.post("/process-query", response_model=Dict[str, Any])
async def process_query(payload: UserQuerySchema = Body(...), current_user = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Processes the initial user query to start planning a trip. It runs the
    query through the workflow and determines if more information is needed.
    """
    try:
        # Initialize the state with the user's raw query. Accept both 'id'
        # and '_id' keys from the current_user dict for robustness.
        user_id = None
        if isinstance(current_user, dict):
            user_id = current_user.get("id") or current_user.get("_id")

        initial_state = {"additional_info": payload.query, "user_id": user_id}
        # Run the workflow to extract information from the query
        result_state = workflow.invoke(initial_state)

        # Persist the initial user query as a conversation (best-effort).
        # If saving fails we still return the response to the client.
        try:
            if user_id:
                created = await create_conversation(user_id, None, None)
                if created and created.get("id"):
                    conv_id = created.get("id")
                    ok = await append_message(conv_id, "user", payload.query, {})
                    if not ok:
                        print(f"Warning: append_message returned False for conversation {conv_id}")
                    else:
                        print(f"Saved initial query to conversation {conv_id}")
        except Exception as e:
            # Log but don't break the API response
            print("Error while saving conversation:", type(e).__name__, str(e))

        # Build the response based on the workflow's output
        final_response = _build_final_response(result_state)

        # Persist assistant response as a message (best-effort). If saving
        # fails we still return the response to the client.
        try:
            if user_id and created and created.get("id"):
                # Convert final_response to a compact text representation for storage
                # Keep it simple: JSON-like string or join the relevant fields
                import json
                assistant_text = json.dumps(final_response, default=str)
                ok2 = await append_message(created.get("id"), "assistant", assistant_text, {})
                if not ok2:
                    print(f"Warning: failed to append assistant message to conversation {created.get('id')}")
                else:
                    print(f"Saved assistant response to conversation {created.get('id')}")
        except Exception as e:
            print("Error while saving assistant response:", type(e).__name__, str(e))

        return final_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@router.post("/answer-followup", response_model=Dict[str, Any])
async def answer_followup(payload: FollowUpPayload = Body(...)) -> Dict[str, Any]:
    """
    Processes a user's answers to follow-up questions. It merges the new
    answers with the previous state and re-runs the workflow.
    """
    try:
        # Merge the previous state with the new answers to ensure continuity
        updated_state_data = payload.current_state
        updated_state_data.update(payload.answers)

        # Pass the new answers as 'additional_info' for contextual processing
        updated_state_data['additional_info'] = " ".join(map(str, payload.answers.values()))

        # Re-run the workflow with the combined information
        result_state = workflow.invoke(updated_state_data)

        # Build and return the final response
        return _build_final_response(result_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")