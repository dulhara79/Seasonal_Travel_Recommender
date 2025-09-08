# Entry point for orchestrator to call

# Expose functions your orchestrator can call, e.g., get_activity_suggestions()

from server.agents.activity_agent.azure_client import get_activity_suggestions
from server.agents.activity_agent.recommender import build_prompt


def handle_request(request, full_request):
    prompt = build_prompt(request.destination, request.dates, request.weather, request.preference)
    activities = get_activity_suggestions(prompt)
    
    if full_request:
        # Send activities to both orchestrator and packing agent
        pass
    else:
        # Send activities to orchestrator only
        pass

