from server.agents.orchestrator_agent.orchestrator_agent import call_orchestrator_agent
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema


def test_duration_then_start_calculates_end_date():
    # User initially says: "Plan a 7-day trip to Sri Lanka for a family..."
    # This would produce a state with trip_duration = '7 days' (LLM extraction step)
    initial_state = OrchestratorAgent4InputSchema(query="Plan a 7-day trip to Sri Lanka for a family of 3")

    # Run orchestrator once to get initial extraction (non-interactive)
    result = call_orchestrator_agent(initial_state)

    # It should ask for start_date (since start_date is missing)
    assert result.status == "awaiting_user_input"
    assert any(m['field'] == 'start_date' for m in [x.dict() for x in result.messages])

    # Now simulate user providing start date: "14th oct 2025"
    followup_state = OrchestratorAgent4InputSchema(query="14th oct 2025")

    # Provide previous JSON state as prev_json_response to carry over trip_duration
    prev = result.dict()

    result2 = call_orchestrator_agent(followup_state, user_responses=["14th oct 2025"], prev_json_response=prev)

    # After applying start date, the orchestrator should compute end_date = 2025-10-20
    assert result2.status in ("awaiting_user_input", "complete")
    assert result2.start_date == "2025-10-14"
    assert result2.end_date == "2025-10-20"
