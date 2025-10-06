import re
from datetime import datetime, date, timedelta
from json import JSONDecodeError

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
from typing import Optional, Tuple
import json

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException

# NOTE: Replace with your actual schema imports
from server.schemas.orchestrator_schemas import (
    OrchestratorExtractionSchema,
    OrchestratorAgent4OutputSchema,
    # OrchestratorAgent4InputSchema (not used in this module)
)

# --- CONSTANTS ---
CURRENT_DATETIME = datetime.now()
CURRENT_DATE = CURRENT_DATETIME.date()
CURRENT_DATE_STR = CURRENT_DATE.strftime("%Y-%m-%d")
MAX_FUTURE_DATE = (CURRENT_DATETIME + relativedelta(years=2)).date()
MAX_TRIP_DAYS = 60

MANDATORY_FIELDS = [
    "destination",
    "start_date",
    "end_date",  # Included, but conditionally checked in orchestrator_agent.py
    "no_of_traveler",
    "type_of_trip",
    "user_preferences",
]

SRI_LANKA_SEASONS = {
    range(5, 10): "Southwest Monsoon",
    tuple(list(range(10, 13)) + [1]): "Northeast Monsoon",
    range(2, 5): "Inter-monsoon",
}

SW_MONSOON_AFFECTED_AREAS = [
    'galle', 'bentota', 'mirissa', 'colombo', 'unawatuna', 'hikkaduwa', 'weligama', 'mount lavinia',
    'kandy', 'nuwara eliya', 'ella', 'haputale'
]


# --- HELPER FUNCTIONS (Identical to previous correct version) ---

def _parse_traveler_from_text(text: str) -> Optional[int]:
    """Attempts to parse common traveler count terms from text."""
    if not text:
        return None
    text_lower = text.lower()
    if 'solo' in text_lower or 'single' in text_lower:
        return 1
    if 'dual' in text_lower or 'couple' in text_lower or 'two people' in text_lower:
        return 2
    match = re.search(r'(\d+)', text_lower)
    if match:
        try:
            num = int(match.group(1))
            if num > 0:
                return num
        except ValueError:
            pass  # Keep looking if the captured part isn't a valid number

    # Old: Check for standalone digits (will only catch "4")
    try:
        if text.strip().isdigit():
            num = int(text.strip())
            if num > 0:
                return num
    except ValueError:
        pass

    return None


def _parse_duration(duration_str: Optional[str]) -> Optional[int]:
    """Converts a trip duration string (e.g., '2 day', 'two weeks') into a total number of days."""
    if not duration_str:
        return None

    # Accept integers that may have been set by previous validation steps
    if isinstance(duration_str, int):
        return duration_str

    text_lower = duration_str.lower()

    # Handle numeric word to digit conversion for days/weeks/months
    num_map = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
               'ten': 10}

    # Accept formats like '7 day', '7-day', '7days', 'seven-day', 'two weeks', etc.
    # Allow optional hyphen or no space between the number/word and the unit.
    number_group = r'(\d+|' + '|'.join(num_map.keys()) + r')'
    unit_group = r'(day|week|month)s?'
    match = re.search(number_group + r'\s*[-]?\s*' + unit_group, text_lower)

    if match:
        num_str = match.group(1)
        unit = match.group(2)

        # Convert word to number if necessary
        num = int(num_str) if num_str.isdigit() else num_map.get(num_str, 0)

        if num <= 0:
            return None

        if unit.startswith('day'):
            return num
        elif unit.startswith('week'):
            return num * 7
        elif unit.startswith('month'):
            # Approximation for planning: 30 days per month
            return num * 30

    # Handle single digit/numeric string answer (e.g., user answers '4' to 'how many days?')
    try:
        if text_lower.strip().isdigit():
            num = int(text_lower.strip())
            if num > 0:
                return num
    except ValueError:
        pass

    # As a last attempt, handle compact forms like '7d', '10w' (common shorthand)
    m = re.search(r"(\d+)\s*(d|day|days|w|week|weeks|m|month|months)\b", text_lower)
    if m:
        n = int(m.group(1))
        u = m.group(2)
        if u.startswith('d'):
            return n
        if u.startswith('w'):
            return n * 7
        if u.startswith('m'):
            return n * 30

    return None


def get_sri_lanka_season(dt: date) -> str | None:
    """Infers the Sri Lankan season from a date object."""
    month = dt.month
    for month_range, season in SRI_LANKA_SEASONS.items():
        if isinstance(month_range, range) and month in month_range:
            return season
        if isinstance(month_range, tuple) and month in month_range:
            return season
    return None


def _flexible_date_parse(date_str: str) -> Optional[date]:
    """
    Parses a flexible date string and returns a date object, or None on failure.
    Uses CURRENT_DATETIME as the reference point for relative dates (e.g., 'next week').
    """
    if not date_str:
        return None
    try:
        # Primary attempt: prefer day-first formats (common in Sri Lanka)
        parsed_dt = dateutil_parser.parse(date_str, fuzzy=True, dayfirst=True, default=CURRENT_DATETIME)
        return parsed_dt.date()
    except Exception:
        # Secondary attempt: try month-first in case user used an ambiguous format
        try:
            parsed_dt = dateutil_parser.parse(date_str, fuzzy=True, dayfirst=False, default=CURRENT_DATETIME)
            return parsed_dt.date()
        except Exception as e:
            # Give up and return None; caller will handle missing dates
            print(f"Date parsing failed for '{date_str}': {e}")
            return None


def safe_parse(output_parser: PydanticOutputParser, text: str,
               prev_response: Optional[OrchestratorAgent4OutputSchema] = None) -> OrchestratorExtractionSchema:
    """Safely parses LLM output, providing a fallback mechanism that preserves prior state."""
    try:
        # 1. Attempt to parse the new LLM output directly
        new_extraction = output_parser.parse(text).dict()

        # 2. Merge with previous state if it exists
        if prev_response:
            # Start with the old, validated data
            merged_data = prev_response.dict()

            # --- START OF FIX: Define fields to STRICTLY preserve unless explicitly provided ---
            # These are facts that, once established, should only be overwritten if the LLM
            # provides a clear, new, non-null value for them.
            PRESERVE_FIELDS = ["trip_duration", "no_of_traveler", "destination"]

            # Overwrite old fields with any new, non-null values from the LLM extraction
            for k, v in new_extraction.items():
                is_new_value = v not in (None, "", [])

                if k in merged_data:

                    if k in PRESERVE_FIELDS and merged_data[k] not in (None, "", []) and not is_new_value:
                        # If it's a preserved field, it had a value before, and the LLM's new output is null/empty,
                        # WE KEEP THE OLD VALUE. Skip updating merged_data[k].
                        continue

                    # Special handling for user_preferences (merge/replace lists)
                    if k == "user_preferences" and isinstance(v, list):
                        merged_data[k] = v
                    elif is_new_value:
                        # For all other fields (dates, types, etc.) or when LLM provides a new value for a preserved field
                        merged_data[k] = v
                    elif merged_data.get(k) in (None, "", []) and is_new_value:
                        # If old state was null/empty and new extraction has a value, use it (should be redundant now)
                        merged_data[k] = v

            # Re-parse the merged dictionary back to the extraction schema for validation checks
            return PydanticOutputParser(pydantic_object=OrchestratorExtractionSchema).parse(json.dumps(merged_data))

        # 3. If no previous response, return the new extraction
        return PydanticOutputParser(pydantic_object=OrchestratorExtractionSchema).parse(json.dumps(new_extraction))

    except (OutputParserException, JSONDecodeError) as e:
        print(f"OutputParserException caught: {e}. Attempting to use a fallback structure.")

        fallback_data = {
            "destination": None, "season": None, "start_date": None, "end_date": None,
            "trip_duration": None, "no_of_traveler": None, "budget": None,
            "user_preferences": [], "type_of_trip": None,
        }

        # Preserve previous state in fallback if parsing failed completely
        if prev_response:
            prev_dict = prev_response.dict()
            for k, v in prev_dict.items():
                if v not in (None, "", []) and k in fallback_data:
                    fallback_data[k] = v

        try:
            # Attempt to extract partial data from the raw text if it looks like malformed JSON
            if text.strip().startswith('{') and text.strip().endswith('}'):
                partial_data = json.loads(text.strip())
                fallback_data.update(
                    {k: v for k, v in partial_data.items() if k in fallback_data and v not in (None, "")})

            return PydanticOutputParser(pydantic_object=OrchestratorExtractionSchema).parse(json.dumps(fallback_data))
        except Exception as inner_e:
            print(f"ERROR: Failed to parse fallback structure. {inner_e}")
            raise e  # Re-raise the error if fallback fails


# --- CORE VALIDATION & POST-PROCESSING (FIXED LOGIC) ---

def validate_and_correct_trip_data(
        json_response: dict,
        sanitized_query: str
) -> Tuple[dict, list]:
    """
    Applies all non-LLM based validation and consistency checks
    to the extracted data. Modifies json_response in place.
    """
    messages = []

    # --- 1. TRAVELER VALIDATION (Same) ---
    if json_response.get("no_of_traveler") is None:
        traveler_count = _parse_traveler_from_text(sanitized_query)
        if traveler_count:
            json_response["no_of_traveler"] = traveler_count

    if isinstance(json_response.get("no_of_traveler"), int) and json_response["no_of_traveler"] <= 0:
        print("Validation: Traveler count is 0 or less. Setting to null.")
        json_response["no_of_traveler"] = None

    # --- 2. DATE PARSING & INITIAL VALIDATION (Preserve raw inputs) ---
    # Capture raw strings before we overwrite them with ISO values
    raw_start = json_response.get("start_date")
    raw_end = json_response.get("end_date")

    start_dt = _flexible_date_parse(raw_start) if raw_start else None
    end_dt = _flexible_date_parse(raw_end) if raw_end else None

    # --- 3. DURATION CALCULATION AND END DATE INFERENCE (CRITICAL FIX HERE) ---
    trip_duration_days = _parse_duration(json_response.get("trip_duration"))

    # If LLM extraction didn't capture trip_duration, try to infer it from the original sanitized query
    if trip_duration_days is None:
        inferred_duration = _parse_duration(sanitized_query)
        if inferred_duration is not None:
            trip_duration_days = inferred_duration
            json_response["trip_duration"] = trip_duration_days
            messages.append({
                "type": "advisory",
                "field": "trip_duration",
                "message": f"Trip duration inferred as {trip_duration_days} days from your message."
            })

    if trip_duration_days is not None:
        # Ensure trip_duration is stored as an integer for consistency
        json_response["trip_duration"] = trip_duration_days

        if start_dt:
            # Calculate end date based on the user's stated duration (N days = N-1 days after start date)
            calculated_end_dt = start_dt + timedelta(days=trip_duration_days - 1)

            # **CRITICAL CONFLICT RESOLUTION**
            if end_dt and end_dt != calculated_end_dt:
                # Calculate duration from the *user's provided dates*
                duration_from_dates = (end_dt - start_dt).days + 1

                # If there is a conflict (e.g., stated 2 days, but dates imply 3 days)
                if duration_from_dates != trip_duration_days:
                    # We prioritize the user's *stated duration* (e.g., 2 days) over their manual end date
                    end_dt = calculated_end_dt

                    messages.append({
                        "type": "advisory",
                        "field": "end_date",
                        "message": f"Conflict detected: The dates provided ({start_dt.isoformat()} to {end_dt.isoformat()}) imply a {duration_from_dates}-day trip, but the stated duration is {trip_duration_days} days. The trip end date has been corrected to {end_dt.isoformat()} to match the stated duration."
                    })

                # If the dates match the duration (e.g., start 12, end 13, duration 2), do nothing, end_dt is fine.

            elif not end_dt:
                # If no end_dt was provided, use the calculated one
                end_dt = calculated_end_dt
                messages.append({
                    "type": "advisory",
                    "field": "end_date",
                    "message": f"End date calculated as {end_dt.isoformat()} based on start date and {trip_duration_days} days duration."
                })
                # Add a follow-up confirmation asking the user to confirm the calculated end date
                # Build friendly date strings without platform-specific directives
                end_friendly = f"{end_dt.strftime('%B')} {end_dt.day}, {end_dt.year}"
                start_friendly = f"{start_dt.strftime('%B')} {start_dt.day}, {start_dt.year}"
                messages.append({
                    "type": "followup",
                    "field": "end_date",
                    "question": f"I calculated {end_friendly} as the end date based on your {trip_duration_days}-day trip starting on {start_friendly}. Is that correct?"
                })

            # **IMPORTANT:** Update the response dict with the resolved/calculated end_dt
            if end_dt:
                json_response["end_date"] = end_dt.isoformat()

    # --- 4. DATE VALIDATION (Now working with potentially calculated dates) ---

    # Reset dates if they are past/present. Keep original parsed values in temp vars
    for dt_key, dt_val in [("start_date", start_dt), ("end_date", end_dt)]:
        if dt_val and dt_val <= CURRENT_DATE:
            print(f"Validation: {dt_key.capitalize()} {dt_val} is past/present. Setting to null.")
            # Do not overwrite json_response yet; update temp vars
            if dt_key == "start_date":
                start_dt = None
            if dt_key == "end_date":
                end_dt = None

            messages.append({
                "type": "warning",
                "field": dt_key,
                "message": f"The provided {dt_key.replace('_', ' ')} is in the past or today. Please choose a future date."
            })

    # Check if end date is before start date
    if start_dt and end_dt and end_dt < start_dt:
        # Attempt reparsing of the raw_end with explicit alternate dayfirst preferences
        reparsed_end = None
        if raw_end:
            # Try month-first parse then day-first parse to handle ambiguous inputs
            try:
                reparsed_end = dateutil_parser.parse(raw_end, fuzzy=True, dayfirst=False, default=CURRENT_DATETIME).date()
            except Exception:
                try:
                    reparsed_end = dateutil_parser.parse(raw_end, fuzzy=True, dayfirst=True, default=CURRENT_DATETIME).date()
                except Exception:
                    reparsed_end = None

        if reparsed_end and reparsed_end >= start_dt:
            end_dt = reparsed_end
            messages.append({
                "type": "advisory",
                "field": "end_date",
                "message": f"End date re-parsed as {end_dt.isoformat()} and accepted."
            })
        else:
            print("Validation: End Date is before Start Date. Setting End Date to null.")
            end_dt = None
            messages.append({
                "type": "warning",
                "field": "end_date",
                "message": "The end date cannot be before the start date. Please re-enter the end date."
            })

    # After all validation and possible corrections, write back ISO strings for any valid dates
    if start_dt:
        json_response["start_date"] = start_dt.isoformat()
    else:
        json_response["start_date"] = None

    if end_dt:
        json_response["end_date"] = end_dt.isoformat()
    else:
        # Keep it None if not determined
        json_response["end_date"] = None

    # --- 5. POST-PROCESSING (Season/Dest) ---
    if start_dt:
        json_response["season"] = get_sri_lanka_season(start_dt)

    if json_response.get("destination"):
        dest = json_response["destination"].lower()
        json_response["destination"] = dest.title()  # Normalize case

    return json_response, messages