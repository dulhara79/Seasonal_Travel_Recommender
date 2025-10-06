from server.agents.orchestrator_agent.orchestrator_utils import validate_and_correct_trip_data


def test_end_date_inferred_from_duration_and_start():
    # User provided a 2-day trip starting on 2025-10-13
    json_response = {
        "destination": "Anuradhapura",
        "start_date": "13th Oct 2025",
        "end_date": None,
        "trip_duration": "2 day",
        "no_of_traveler": None,
        "type_of_trip": None,
        "user_preferences": []
    }

    sanitized_query = "2 day trip to Anuradhapura starting 13th Oct 2025"

    updated, messages = validate_and_correct_trip_data(json_response, sanitized_query)

    # The util calculates end_date as start + (duration - 1)
    # So a 2-day trip starting 2025-10-13 should end on 2025-10-14
    assert updated["end_date"] == "2025-10-14"
    # Ensure an advisory message about calculation was added
    assert any(m.get("field") == "end_date" for m in messages)
