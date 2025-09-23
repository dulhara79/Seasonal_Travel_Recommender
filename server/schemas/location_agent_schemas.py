# schemas.py
# ----------------------
# Pydantic schemas for the Seasonal Travel Recommender System
# ----------------------

from pydantic import BaseModel
from typing import Optional, List

class LocationAgentInputSchema(BaseModel):
    """
    Input schema for the Location Agent.
    Defines the structure of user-provided travel details.
    """
    destination: Optional[str] = None           # User's chosen travel destination
    start_date: Optional[str] = None            # Trip start date (YYYY-MM-DD)
    end_date: Optional[str] = None              # Trip end date (YYYY-MM-DD)
    user_preferences: List[str] = []            # List of user preferences (e.g., hiking, culture)
    type_of_trip: Optional[str] = None          # Type of trip (adventure, relaxation, cultural, etc.)
    no_of_traveler: Optional[int] = 1           # Number of travelers
    budget: Optional[str] = "medium"            # Budget range (low, medium, high)

class RecommendedLocation(BaseModel):
    """
    Schema for a single recommended location object.
    """
    name: str                                   # Name of the location
    type: str                                   # Type (cultural, scenic, hiking/nature, etc.)
    reason: str                                 # Why this location is recommended

class LocationAgentOutputSchema(BaseModel):
    """
    Output schema for the Location Agent.
    Defines the structure of agent-generated recommendations.
    """
    recommended_locations: List[RecommendedLocation] = []  # Detailed recommended places
    status: Optional[str] = "awaiting_location"            # Status: awaiting_location / complete
    messages: List[dict] = []                              # Any extra system/agent messages
    disclaimer: Optional[str] = "Recommendations are generated fairly and do not store personal user data."
