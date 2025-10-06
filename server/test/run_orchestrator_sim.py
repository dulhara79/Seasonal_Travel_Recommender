import sys
sys.path.insert(0, r'C:\Users\dulha\GitHub\Seasonal_Travel_Recommender')
from server.schemas.orchestrator_schemas import OrchestratorAgent4InputSchema
from server.agents.orchestrator_agent.orchestrator_agent import call_orchestrator_agent
import json

print('=== STEP 1: User says: i want to plan 3 day trip to galle')
state1 = OrchestratorAgent4InputSchema(query='i want to plan 3 day trip to galle')
res1 = call_orchestrator_agent(state1)
print(json.dumps(res1.dict(), indent=2))

print('\n=== STEP 2: User replies with start date: 2025 oct 14')
state2 = OrchestratorAgent4InputSchema(query='2025 oct 14')
prev = res1.dict()
res2 = call_orchestrator_agent(state2, user_responses=['2025 oct 14'], prev_json_response=prev)
print(json.dumps(res2.dict(), indent=2))
