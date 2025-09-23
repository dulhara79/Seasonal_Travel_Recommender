# server/api/route.py

from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
from server.schemas.global_schema import TravelState
from server.schemas.userQuery_schema import UserQuerySchema
from server.workflow.graph_builder import build_graph

# Build the workflow graph
workflow = build_graph()

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

def _build_final_response(state: TravelState) -> Dict[str, Any]:
    """
    Analyzes the state and builds the appropriate API response.

    - If required information is missing, it returns a 'followup_required' response.
    - If all required information is present, it returns a 'complete' response.
    """
    missing_fields = [
        field for field in REQUIRED_QUESTIONS
        if not getattr(state, field, None)  # Safely check if the attribute is missing or empty
    ]

    if missing_fields:
        # Generate questions for the fields that are still missing
        questions_to_ask = [REQUIRED_QUESTIONS[field] for field in missing_fields]
        return {
            "status": "followup_required",
            "missing_fields": missing_fields,
            "questions": questions_to_ask,
            "current_state": state.dict(),
        }
    else:
        # All required info is present, return the final trip plan
        return {
            "status": "complete",
            "trip_plan": {
                "destination": state.destination,
                "start_date": str(state.start_date) if state.start_date else None,
                "end_date": str(state.end_date) if state.end_date else None,
                "no_of_traveler": state.no_of_traveler,
                "type_of_trip": state.type_of_trip,
                "season": state.season,
                "budget": state.budget,
                "preferences": state.user_preferences,
                "locations_to_visit": state.locations_to_visit,
                "activities": state.activities,
                "summary": state.summary,
            },
        }


# --- API Endpoints ---

@router.post("/process-query", response_model=Dict[str, Any])
async def process_query(payload: UserQuerySchema = Body(...)) -> Dict[str, Any]:
    """
    Processes the initial user query to start planning a trip. It runs the
    query through the workflow and determines if more information is needed.
    """
    try:
        # Initialize the state with the user's raw query
        initial_state = {"additional_info": payload.query}

        # Run the workflow to extract information from the query
        result_state = workflow.invoke(initial_state)

        # Build and return the response based on the workflow's output
        return _build_final_response(result_state)
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