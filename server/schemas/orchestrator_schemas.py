from typing import Optional, List

from pydantic import Field, BaseModel


class Message(BaseModel):
    """Schema for system/agent messages to the user (warnings, advisories, followups)."""
    type: str = Field(..., description="Type of message: 're_track', 'followup', 'warning', 'advisory'.")
    field: Optional[str] = Field(None, description="The field the message pertains to.")
    question: Optional[str] = Field(None, description="The question text for followups/re-tracks.")
    message: Optional[str] = Field(None, description="The warning or advisory text.")

class OrchestratorAgent4InputSchema(BaseModel):
    """Input state for the Orchestrator Agent."""
    query: str = Field(..., description="The user's latest query or response.")

class OrchestratorAgent4OutputSchema(BaseModel):
    """Final output structure of the Orchestrator Agent's state."""
    destination: Optional[str] = Field(None, description="The travel destination within Sri Lanka.")
    start_date: Optional[str] = Field(None, description="The trip start date (YYYY-MM-DD).")
    end_date: Optional[str] = Field(None, description="The trip end date (YYYY-MM-DD).")
    trip_duration: Optional[int] = Field(None, description="The trip duration in days.")
    no_of_traveler: Optional[int] = Field(None, description="The number of travelers.")
    season: Optional[str] = Field(None, description="The inferred Sri Lankan travel season.")
    budget: Optional[str] = Field(None, description="The budget (low, medium, high, luxury).")
    user_preferences: List[str] = Field(default_factory=list, description="List of user preferences (e.g., beaches, culture).")
    type_of_trip: Optional[str] = Field(None, description="The type of trip (e.g., family, honeymoon, leisure).")
    status: str = Field(..., description="Current status: 'awaiting_user_input' or 'complete'.")
    messages: List[Message] = Field(default_factory=list, description="List of messages (questions/warnings) for the user.")

# --- Extraction Schema (Temporary for LLM Parsing) ---

class OrchestratorExtractionSchema(BaseModel):
    """
    Temporary schema used directly by the LLM for raw extraction. 
    Includes raw text fields like 'trip_duration' that are validated/transformed later.
    """
    destination: Optional[str] = Field(None, description="The travel destination. Set to null if foreign.")
    start_date: Optional[str] = Field(None, description="The trip start date (raw text or date string).")
    end_date: Optional[str] = Field(None, description="The trip end date (raw text or date string).")
    trip_duration: Optional[str | int] = Field(None, description="The duration of the trip (e.g., '5 days', '2 weeks' or integer days). Null if not given.")
    no_of_traveler: Optional[int] = Field(None, description="The number of travelers. Infer from text.")
    season: Optional[str] = Field(None, description="The Sri Lankan travel season inferred from the date.")
    budget: Optional[str] = Field(None, description="The budget (low, medium, high, luxury).")
    user_preferences: List[str] = Field(default_factory=list, description="A list of user preferences.")
    type_of_trip: Optional[str] = Field(None, description="The type of trip (e.g., family, honeymoon, leisure).")