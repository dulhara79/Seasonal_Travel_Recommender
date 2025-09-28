from server.agents.summary_agent.summary_agent import generate_summary


def test_generate_summary_with_raw_recommendations():
    state = {
        "destination": "Galle",
        "start_date": "2025-12-10",
        "end_date": "2025-12-12",
        "no_of_traveler": 2,
        "budget": "medium",
        "user_preferences": ["beach", "photography"],
        "type_of_trip": "leisure",
        "locations_to_visit": ["Galle Fort"],
        "location_recommendations": {
            "recommended_locations": [
                {"name": "Galle Fort", "type": "historic", "reason": "Great for sunset and colonial architecture", "source": "example.com"}
            ],
            "status": "complete"
        },
        "activity_recommendations": {
            "day_plans": [
                {"date": "2025-12-10", "suggestions": [
                    {"time_of_day": "morning", "title": "Walk the fort", "why": "Beautiful architecture", "source_hints": ["example.com"]}
                ]}
            ],
            "status": "complete"
        },
        "packing_list": {"categories": []},
        "additional_info": "Some extra notes",
        "messages": []
    }

    out = generate_summary(state, use_llm=False)
    assert out.summary is not None
    txt = out.summary
    # Check for key sections
    assert "Trip Summary for" in txt
    assert "Locations to Visit" in txt or "Locations to Visit — Details" in txt
    assert "Responsible AI" in txt or "Responsible AI & Data Notes" in txt
    print("Summary generated successfully:\n", txt[:400])


if __name__ == "__main__":
    test_generate_summary_with_raw_recommendations()
