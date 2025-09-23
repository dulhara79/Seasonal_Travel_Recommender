from server.agents.activity_agent.activity_indexer import suggest_activities
import pprint

inp = {
    "destination": "Kandy, Sri Lanka",
    "start_date": "2025-12-10",
    "end_date": "2025-12-11",
    "user_preferences": ["hiking", "culture"],
    "budget": "medium",
    "type_of_trip": "adventure"
}

out = suggest_activities(inp)

# --- Option A: Pretty-print JSON ---
import json
print(json.dumps(out, indent=2, ensure_ascii=False))

# --- Option B: Friendly human-readable format ---
def print_plan(plan: dict):
    print(f"\n📍 Destination: {plan['destination']}")
    print(f"🎯 Theme: {plan['overall_theme']}")
    print(f"📝 Notes: {plan.get('notes','')}\n")
    for day in plan["day_plans"]:
        print(f"📅 {day['date']}")
        for s in day["suggestions"]:
            print(f"  - {s['time_of_day'].capitalize()}: {s['title']} — {s['why']}")
        print()

print_plan(out)

