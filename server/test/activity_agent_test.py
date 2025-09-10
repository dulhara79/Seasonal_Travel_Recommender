import os

from server.agents.activity_agent_1.activity_agent import build_or_refresh_index, INDEX_DIR, suggest_activities
from server.schemas.activity_schemas import ActivityAgentInput

if __name__ == "__main__":
    # Initial one-time index build
    if not os.path.isdir(INDEX_DIR):
        print("Building index…")
        build_or_refresh_index()


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
    out = suggest_activities(sample)
    print(out)