# from server.agents.activity_agent.activity_indexer import suggest_activities
# import pprint

# inp = {
#     "destination": "Kandy, Sri Lanka",
#     "start_date": "2025-12-10",
#     "end_date": "2025-12-11",
#     "user_preferences": ["hiking", "culture"],
#     "budget": "low",
#     "type_of_trip": "adventure"
# }

# out = suggest_activities(inp)

# # --- Option A: Pretty-print JSON ---
# import json
# print(json.dumps(out, indent=2, ensure_ascii=False))

# # --- Option B: Friendly human-readable format ---
# def print_plan(plan: dict):
#     print(f"\n📍 Destination: {plan['destination']}")
#     print(f"🎯 Theme: {plan['overall_theme']}")
#     print(f"📝 Notes: {plan.get('notes','')}\n")
#     for day in plan["day_plans"]:
#         print(f"📅 {day['date']}")
#         for s in day["suggestions"]:
#             print(f"  - {s['time_of_day'].capitalize()}: {s['title']} — {s['why']}")
#         print()

# print_plan(out)



# server/agents/activity_agent/activity_testing.py
from server.agents.activity_agent.activity_indexer import suggest_activities
import json
import sys
import traceback

inp = {
    "destination": "Kandy, Sri Lanka",
    "start_date": "2025-12-10",
    "end_date": "2025-12-11",
    "user_preferences": ["hiking", "culture"],
    "budget": "low",
    "type_of_trip": "adventure"
}

def safe_print_json(obj):
    try:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    except Exception:
        # fallback for objects that are not JSON-serializable
        print(str(obj))

def format_confidence(c):
    try:
        if c is None:
            return ""
        return f" (confidence: {float(c):.2f})"
    except Exception:
        return f" (confidence: {c})"

def print_plan(plan: dict):
    """
    Friendly human-readable output for activity plans.
    Defensive: handles missing keys gracefully.
    """
    if not isinstance(plan, dict):
        print("\nUnexpected plan format (not a dict):")
        print(plan)
        return

    destination = plan.get("destination", "Unknown destination")
    overall_theme = plan.get("overall_theme", "")
    notes = plan.get("notes", "")
    top_sources = plan.get("top_sources", []) or []

    print("\n📍 Destination:", destination)
    if overall_theme:
        print("🎯 Theme:", overall_theme)
    if notes:
        print("📝 Notes:", notes)
    if top_sources:
        print("\n🔎 Top sources used:")
        for s in top_sources:
            print("  -", s)

    day_plans = plan.get("day_plans", [])
    if not day_plans:
        print("\n(No day plans returned.)")
        return

    for day in day_plans:
        date = day.get("date", "unknown date")
        print(f"\n📅 {date}")
        suggestions = day.get("suggestions", [])
        if not suggestions:
            print("  (no suggestions)")
            continue

        for s in suggestions:
            tod = s.get("time_of_day", "time")
            title = s.get("title", "No title")
            why = s.get("why", "")
            confidence = s.get("confidence", None)
            source_hints = s.get("source_hints", None)

            # Print main line with confidence if exists
            conf_str = format_confidence(confidence)
            print(f"  - {tod.capitalize()}: {title}{conf_str}")
            if why:
                print(f"      → {why}")

            # Prefer per-suggestion source_hints; fall back to top_sources
            sources_to_show = None
            if isinstance(source_hints, list) and source_hints:
                sources_to_show = source_hints
            elif top_sources:
                sources_to_show = top_sources

            if sources_to_show:
                # print up to 3 sources to keep output compact
                show_sources = sources_to_show[:3]
                print("      sources:", ", ".join(show_sources))

if __name__ == "__main__":
    try:
        out = suggest_activities(inp)
    except Exception as e:
        print("Error while calling suggest_activities:")
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    # Option A: Pretty-print raw JSON result for debugging / saving
    print("\n==== RAW JSON OUTPUT ====\n")
    safe_print_json(out)

    # Option B: Friendly human-readable format for quick demo / viva
    print("\n==== FRIENDLY OUTPUT ====\n")
    print_plan(out)
