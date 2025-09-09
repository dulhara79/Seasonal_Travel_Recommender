# main.py

from conversation_agent import get_user_inputs
from travel_recommendation_agent import recommend_places
from activity_agent import generate_activity_plan

# Step 1: Get user input
user_vars = get_user_inputs()

# Step 2: Get recommended places
places = recommend_places(user_vars)

if not places:
    print("Sorry, no attractions found for your input.")
else:
    print("\nRecommended Places:", places)

    # Step 3: Generate activity plan
    itinerary = generate_activity_plan(
        places,
        user_vars["location"],
        user_vars["start_date"],
        user_vars["end_date"]
    )

    print("\nSuggested Activities / Itinerary:\n", itinerary)
