from server.agents.activity_agent.activity_indexer import suggest_activities

inp = {
    "destination": "Kandy, Sri Lanka",
    "start_date": "2025-12-10",
    "end_date": "2025-12-11",
    "user_preferences": ["hiking", "culture"],
    "budget": "medium",
    "type_of_trip": "adventure"
}

out = suggest_activities(inp)
print(out)
