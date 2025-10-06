# server/agents/activity_agent/activity_testing.py
"""Run a test for suggest_activities and print both raw JSON and a friendly, diagnostic summary.
Saves raw JSON to server/agents/activity_agent/activity_test_output.json for inspection.
"""
import json
import sys
import traceback
import argparse
from datetime import datetime
from statistics import mean

from server.agents.activity_agent.activity_indexer import suggest_activities

DEFAULT_OUTPUT_PATH = "server/agents/activity_agent/activity_test_output.json"


def parse_args():
    p = argparse.ArgumentParser(description="Test suggest_activities and print human-friendly output.")
    p.add_argument("--destination", default="Galle, Sri Lanka", help="Destination string")
    p.add_argument("--start-date", default=(datetime.today().strftime("%Y-%m-%d")), help="Start date YYYY-MM-DD")
    p.add_argument("--end-date", default=(datetime.today().strftime("%Y-%m-%d")), help="End date YYYY-MM-DD")
    p.add_argument("--budget", default="low", help="Budget preference (low|medium|high)")
    p.add_argument("--prefs", default="hiking,culture", help="Comma-separated user preferences")
    p.add_argument("--type", default="adventure", help="Type of trip")
    p.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Path to save raw JSON output")
    return p.parse_args()


def safe_json_dumps(obj, **kwargs):
    try:
        return json.dumps(obj, **kwargs)
    except Exception:
        # fallback: convert problematic objects to string
        def default(o):
            try:
                return str(o)
            except Exception:
                return "<unserializable>"
        return json.dumps(obj, default=default, **kwargs)


def format_confidence(c):
    try:
        if c is None:
            return ""
        return f" (conf: {float(c):.2f})"
    except Exception:
        return f" (conf: {c})"


def print_plan(plan: dict):
    """Human-friendly printing + diagnostics for the returned plan."""
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
        print("\n🔎 Top sources used (up to 5 shown):")
        for s in top_sources[:5]:
            print("  -", s)

    day_plans = plan.get("day_plans", [])
    if not day_plans:
        print("\n(No day plans returned.)")
        return

    # Diagnostics counters
    total_suggestions = 0
    llm_generated_suggestions = 0
    locality_confidences = []

    # expected days (try to infer)
    try:
        start_date = datetime.strptime(day_plans[0]["date"], "%Y-%m-%d") if day_plans else None
    except Exception:
        start_date = None

    print("\n--- Day-by-day suggestions ---")
    for day in day_plans:
        date = day.get("date", "unknown date")
        print(f"\n📅 {date}")
        suggestions = day.get("suggestions", [])
        if not suggestions:
            print("  (no suggestions)")
            continue

        present_tods = set()
        for s in suggestions:
            total_suggestions += 1
            tod = s.get("time_of_day", "time").lower()
            title = s.get("title", "No title")
            why = s.get("why", "")
            confidence = s.get("confidence", None)
            locality = s.get("locality_confidence", None)
            source_hints = s.get("source_hints", None)

            if locality is not None:
                try:
                    locality_confidences.append(float(locality))
                except Exception:
                    pass

            # detect llm generated hints either in per-suggestion source_hints or top_sources
            combined_sources = []
            if isinstance(source_hints, list):
                combined_sources.extend(source_hints)
            combined_sources.extend(top_sources or [])

            is_llm_generated = any("llm_generated" in (s.lower() if isinstance(s, str) else "") for s in combined_sources)
            if is_llm_generated:
                llm_generated_suggestions += 1

            present_tods.add(tod)

            conf_str = format_confidence(confidence)
            print(f"  - {tod.capitalize()}: {title}{conf_str}")
            if why:
                print(f"      → {why}")
            # show up to 3 source hints
            if isinstance(source_hints, list) and source_hints:
                print("      sources:", ", ".join(source_hints[:3]))

        # completeness check for 4 slots
        missing = [t for t in ("morning", "noon", "evening", "night") if t not in present_tods]
        if missing:
            print(f"  ⚠️ Missing slots for this day: {', '.join(missing)} (placeholders may be used)")

    # Summary diagnostics
    print("\n--- Summary diagnostics ---")
    print("Total days returned:", len(day_plans))
    print("Total suggestions:", total_suggestions)
    print("LLM-generated suggestions (heuristic):", llm_generated_suggestions)
    if locality_confidences:
        try:
            print("Locality confidence — min/avg/max: "
                  f"{min(locality_confidences):.2f} / {mean(locality_confidences):.2f} / {max(locality_confidences):.2f}")
        except Exception:
            print("Locality confidence values:", locality_confidences)
    else:
        print("No locality_confidence values found in suggestions.")

    # Checks and pass/fail notes
    expected_days = None
    try:
        # infer expected from top-level trip if present in plan notes or fields; fallback skip
        expected_days = None
    except Exception:
        expected_days = None

    if expected_days is not None and expected_days != len(day_plans):
        print(f"⚠️ Expected {expected_days} days but got {len(day_plans)} days.")

    print("\nRaw JSON saved to:", args.output)


if __name__ == "__main__":
    args = parse_args()

    # build input dict
    inp = {
        "destination": args.destination,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "user_preferences": [p.strip() for p in args.prefs.split(",") if p.strip()],
        "budget": args.budget,
        "type_of_trip": args.type,
    }

    try:
        out = suggest_activities(inp)
    except Exception:
        print("Error while calling suggest_activities:")
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)

    # Save raw JSON for debugging / CI
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(safe_json_dumps(out, indent=2, ensure_ascii=False))
    except Exception:
        print("Warning: could not save raw JSON output to", args.output)

    # Option A: Pretty-print raw JSON result for debugging / saving
    print("\n==== RAW JSON OUTPUT (truncated preview) ====\n")
    try:
        # print only first N chars for preview
        raw = safe_json_dumps(out, indent=2, ensure_ascii=False)
        print(raw[:2000] + ("\n... (truncated)" if len(raw) > 2000 else ""))
    except Exception:
        print(out)

    # Option B: Friendly human-readable format and diagnostics
    print("\n==== FRIENDLY OUTPUT ====\n")
    print_plan(out)
