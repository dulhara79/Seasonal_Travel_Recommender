import os
from typing import List

# If your teammate's modules are present, you can import them.
# For now, we'll define the exact same shape locally for a self-contained demo.

class ActivityAgentInput:
    def __init__(
        self,
        location: str,
        season: str,
        start_date: str,
        end_date: str,
        preferences: List[str],
        no_of_traveler: int,
        budget: str,
        user_preferences: List[str],
        type_of_trip: str,
        suggest_locations: List[str],
    ):
        self.location = location
        self.season = season
        self.start_date = start_date
        self.end_date = end_date
        self.preferences = preferences
        self.no_of_traveler = no_of_traveler
        self.budget = budget
        self.user_preferences = user_preferences
        self.type_of_trip = type_of_trip
        self.suggest_locations = suggest_locations

    def model_dump(self):
        return dict(
            location=self.location,
            season=self.season,
            start_date=self.start_date,
            end_date=self.end_date,
            preferences=self.preferences,
            no_of_traveler=self.no_of_traveler,
            budget=self.budget,
            user_preferences=self.user_preferences,
            type_of_trip=self.type_of_trip,
            suggest_locations=self.suggest_locations,
        )

# ---------------- Demo starts here ----------------
from .packing_agent import generate_packing_list

if __name__ == "__main__":
    # Sample input exactly like the one you showed
    sample = ActivityAgentInput(
        location="Sri Dalada Maligawa",
        season="summer",
        start_date="2025-09-06",
        end_date="2025-09-08",
        preferences=[],
        no_of_traveler=1,
        budget="medium",
        user_preferences=["village vibes"],
        type_of_trip="solo",
        suggest_locations=["knuckles range", "kandy"],
    )

    # Assume your "suggest_activities" will return a list later.
    # For now, provide a realistic stub:
    suggested_activities = [
        "Temple visit",
        "Hiking in Knuckles range",
        "Tea tasting tour"
    ]

    use_llm = bool(os.getenv("OPENAI_API_KEY"))
    out = generate_packing_list(sample.model_dump(), suggested_activities, use_llm=use_llm)

    import json
    print(json.dumps(out, indent=2, ensure_ascii=False))
