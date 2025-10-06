import json
from typing import List, Dict, Any, Optional

# LangChain Imports
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.chains import LLMChain

# Local Imports
# Assuming your config file has OPENAI_API_KEY and OPENAI_MODEL
from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from server.utils.text_security import sanitize_input
from server.schemas.orchestrator_schemas import (
    OrchestratorAgent4OutputSchema,
    OrchestratorAgent4InputSchema,
    OrchestratorExtractionSchema
)
# This import now points to the FIXED utility file
from server.agents.orchestrator_agent.orchestrator_utils import (
    safe_parse,
    _parse_traveler_from_text,
    validate_and_correct_trip_data,
    CURRENT_DATE_STR
)

# --- 1. INITIALIZATION ---

# NOTE: Replace with your actual LLM initialization logic if different
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.3)
parser = PydanticOutputParser(pydantic_object=OrchestratorExtractionSchema)

# --- 2. EXTRACTION PROMPT & AGENT ---

extraction_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""
            You are a helpful and expert travel assistant that extracts structured trip details for travel planning in **Sri Lanka only**. 
            The **CURRENT DATE is {CURRENT_DATE_STR}**.
            Follow these rules strictly:

            1. **Destination Validation (CRITICAL):**
               - Only accept **Sri Lankan destinations**. 
               - If a foreign location is mentioned, set `"destination": null`. **Do not mention or discuss foreign locations.**

            2. **Date & Duration Extraction (CRITICAL):**
               - **Identify the specific start date in the user's input** and map it directly to the `start_date` field, even if the user uses phrases like 'trip starts on...' or 'date is...'.
               - Extract all date and duration information. Dates (start_date, end_date) can be in **ANY** format (e.g., '2nd March 2025', 'next week'). Output them as the **RAW TEXT** the user provided or the **best YYYY-MM-DD guess** if unambiguous. 
               - Extract the `trip_duration` (e.g., '5 days', '2 weeks') if provided. **Do NOT apply any date validation here.**
               - **If trip duration and trip start date are provided, you MUST extract both and set end_date to null/raw text.** The subsequent logic will calculate the end date.

            3. **Travelers Extraction (Improved):**
               - Extract as an integer. You MUST be able to infer this from words like **'solo trip' (1), 'dual trip' or 'couple' (2), or 'family of X' (X)**. If not provided, set `"no_of_traveler": null`.

            4. **Season (For LLM only):**
               - If dates are given, infer the season based on Sri Lanka’s climate (May–Sept: SW Monsoon, Oct–Jan: NE Monsoon, Feb–April: Inter-monsoon).

            5. **Output Format:**
               - Always respond ONLY with a **single valid JSON object**. No natural language, no extra text.
            """,
        ),
        ("system",
         "Ensure the JSON is correctly formatted and strictly follows the schema. Do not include extra text."),
        ("placeholder", "{chat_history}"),
        ("human", "{user_input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

agent = create_tool_calling_agent(llm=llm, tools=[], prompt=extraction_prompt)
agent_executor = AgentExecutor(agent=agent, tools=[], verbose=True)

# --- 3. QUESTION GENERATOR PROMPT & CHAIN ---

QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a friendly and creative travel assistant for trips to Sri Lanka.
            Your task is to analyze the partially filled trip data and generate a single, friendly, and engaging question to gather the next piece of **mandatory** missing information.
            **Do not** generate a full response or JSON. **Only** output the question text.

            Current Trip Data: {current_data}
            Missing Field to ask for: {missing_field}
            """,
        ),
        ("human", "Generate a question to ask the user for the missing information."),
    ]
)

question_generator_chain = LLMChain(llm=llm, prompt=QUESTION_PROMPT, verbose=False)


def create_followup_questions(json_response: dict, missing_fields: list) -> dict:
    """Generates a creative question for the first missing mandatory field."""
    if not missing_fields:
        return {}

    missing_field = missing_fields[0]

    question_result = question_generator_chain.invoke({
        "current_data": json.dumps(json_response, indent=2),
        "missing_field": missing_field
    })

    question_text = question_result.get('text', f"Please provide the missing information for {missing_field}:").strip()

    return {missing_field: question_text}


# --- 4. CORE EXTRACTION AND VALIDATION STEP ---

def run_llm_agent(
        state: OrchestratorAgent4InputSchema,
        chat_history: List = None,
        prev_response_pydantic: Optional[OrchestratorAgent4OutputSchema] = None
) -> OrchestratorAgent4OutputSchema:
    """Executes the core LLM extraction and applies post-extraction validation/correction."""
    if chat_history is None:
        chat_history = []

    # === SANITIZE INPUT IS HERE ===
    sanitized_query = sanitize_input(state.query)

    if sanitized_query == "LONG_INPUT_STORED":
        # Cannot extract structured data from a long text flag.
        print("INFO: Orchestrator received LONG_INPUT_STORED flag. Cannot process structured extraction.")

        final_response = OrchestratorAgent4OutputSchema(
            status="awaiting_user_input",
            messages=[{
                "type": "warning",
                "field": "query",
                "message": "The query was too long for structured trip planning. Please provide the key details (destination, dates, travelers) in a shorter message."
            }]
        )
        return final_response

    # 1. LLM Extraction
    result = agent_executor.invoke(
        {"user_input": sanitized_query, "chat_history": chat_history}
    )
    result_content = result.get("output", str(result))

    response_pydantic_extract = safe_parse(parser, result_content, prev_response=prev_response_pydantic)
    json_response = response_pydantic_extract.dict()

    # 2. Check for Foreign Destination (pre-validation)
    foreign_destination_detected = False
    if json_response.get("destination") is None and any(word in sanitized_query.lower() for word in
                                                        ['paris', 'tokyo', 'london', 'usa', 'france', 'dubai',
                                                         'maldives', 'singapore']):
        foreign_destination_detected = True

    # 3. Post-Extraction Validation & Correction (This uses the FIXED utility function)
    json_response, messages = validate_and_correct_trip_data(json_response, sanitized_query)

    # Add the status field
    if prev_response_pydantic and prev_response_pydantic.status:
        json_response['status'] = prev_response_pydantic.status
    else:
        json_response['status'] = "awaiting_user_input"

    # 4. Final Conversion and Message Handling
    final_response = OrchestratorAgent4OutputSchema(**{
        k: v for k, v in json_response.items() if k in OrchestratorAgent4OutputSchema.model_fields
    })

    final_response.messages.extend(messages)

    if foreign_destination_detected:
        final_response.destination = None
        final_response.messages.append(
            {"type": "foreign_flag", "field": "destination", "message": "Foreign destination detected."})

    return final_response


# --- 5. MAIN ORCHESTRATOR FUNCTION ---

def call_orchestrator_agent(
        state: OrchestratorAgent4InputSchema,
        user_responses: List[str] = None,
        prev_json_response: Optional[Dict[str, Any]] = None
) -> OrchestratorAgent4OutputSchema:
    """
    Main function for the orchestrator, handles initial extraction and follow-up
    questions for mandatory fields.
    """
    if user_responses is None:
        user_responses = []

    # Keep a sanitized copy of the original user input so follow-up validations
    # can re-parse previously-provided information (like trip_duration).
    sanitized_query = sanitize_input(state.query)

    # Initialize json_response based on previous state or new run
    if prev_json_response:
        json_response = prev_json_response.copy()
        # Clear old temporary messages
        json_response['messages'] = [m for m in json_response.get('messages', []) if
                                     m['type'] in ['warning', 'advisory']]

    else:
        # Initial run: Let LLM fill as much as possible
        response_pydantic = run_llm_agent(state)
        json_response = response_pydantic.dict()

        # Handle Foreign Destination Re-tracking
        if any(m['type'] == 'foreign_flag' for m in json_response.get('messages', [])):
            json_response['messages'] = [m for m in json_response['messages'] if m['type'] != 'foreign_flag']
            retrack_message = {
                "type": "re_track",
                "field": "destination",
                "question": "Thank you! I see you might be planning a trip outside Sri Lanka. As an expert Sri Lanka travel planner, I can only assist with destinations within the island. Would you like to tell me which part of Sri Lanka you're interested in? 🇱🇰"
            }
            json_response["status"] = "awaiting_user_input"
            json_response.setdefault("messages", []).append(retrack_message)
            return OrchestratorAgent4OutputSchema(**json_response)

    while True:
        # Re-evaluate missing fields based on the current state
        missing_fields = []

        # --- FIXED LOGIC: SIMPLER, NON-REDUNDANT CHECK ---

        # Check for destination
        if not json_response.get("destination"):
            missing_fields.append("destination")

        # Check for start_date (we require an ISO start_date after validation)
        if not json_response.get("start_date"):
            missing_fields.append("start_date")

        # Check for end_date (CRITICAL: Only if we can't calculate it)
        # End date is missing ONLY if it's not set AND duration is also not set.
        # This ensures we don't ask for end_date when the user already provided duration
        # (we'll later compute the end_date when a start_date is provided).
        if not json_response.get("end_date") and not json_response.get("trip_duration"):
            missing_fields.append("end_date")

        # Check for no_of_traveler
        if not json_response.get("no_of_traveler"):
            missing_fields.append("no_of_traveler")

        # Check for type_of_trip
        if not json_response.get("type_of_trip"):
            missing_fields.append("type_of_trip")

        # Check for user_preferences
        if not json_response.get("user_preferences"):
            missing_fields.append("user_preferences")

        # NOTE: Removed budget as a strict mandatory field for simple trip planning.
        # NOTE: If we want to strictly follow MANDATORY_FIELDS list, the loop would look like:
        # for f in MANDATORY_FIELDS:
        #    if f == "end_date":
        #        if not json_response.get("end_date") and not json_response.get("trip_duration"):
        #            missing_fields.append(f)
        #    elif not json_response.get(f): # Generic check for all other fields
        #        missing_fields.append(f)

        # Use the explicit, simpler checks above for clarity and to prevent ambiguity.
        # ----------------------------------------------------------------------

        if not missing_fields:
            json_response["status"] = "complete"
            break  # All done!

        missing_field = missing_fields[0]
        questions = create_followup_questions(json_response, missing_fields)

        def apply_answer(field: str, ans: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Applies user answer to the state and returns the updated dictionary.
            It handles special field types and triggers the core validation/correction logic.
            """
            if field == "no_of_traveler":
                # --- START OF FIX ---
                # Attempt to parse the answer into an integer using the helper function.
                count = _parse_traveler_from_text(ans)
                if count is not None and count > 0:
                    current_state[field] = count
                else:
                    # If parsing fails, explicitly set to None (or the LLM's raw output if required,
                    # but for mandatory fields, setting to None is safer to force re-prompting/re-validation).
                    current_state[field] = None # <-- CRITICAL CHANGE: Set to None instead of the raw invalid string
                    # Add a message for the user/system indicating the failure
                    current_state.setdefault("messages", []).append({
                        "type": "warning",
                        "field": "no_of_traveler",
                        "message": f"Could not determine the number of travelers from '{ans}'. Please provide a clear number."
                    })
                # --- END OF FIX ---

            elif field == "user_preferences":
                # Handle the list structure for preferences
                current_state["user_preferences"] = [x.strip() for x in ans.split(",") if x.strip()]

            elif field == "budget":
                # Simple string for budget (e.g., 'luxury', 'mid-range', 'Rs. 50,000')
                current_state[field] = ans.strip()

            else:
                # For 'destination', 'start_date', 'end_date', 'trip_duration', 'type_of_trip': store the raw text
                # The validation function will attempt to parse and standardize it.
                current_state[field] = ans.strip()

            # Rerun validation/correction after applying the new answer (THIS IS CRITICAL)
            # Use the overall sanitized_query (outer scope) rather than the single-field ans
            # so previously provided information (like '2 day trip') is still available
            # and can be parsed into trip_duration/end_date.
            current_state, messages = validate_and_correct_trip_data(current_state, sanitized_query)
            current_state.setdefault("messages", []).extend(messages)

            # EXTRA SAFETY: If the user just provided a start_date or trip_duration and
            # an end_date is still missing, attempt one more explicit calculation so the
            # orchestrator will not prompt the user for an end_date when duration is known.
            try:
                needs_end = (current_state.get("start_date") and not current_state.get("end_date") and
                             current_state.get("trip_duration"))
                if needs_end:
                    # The validator should already have set end_date, but do one more pass
                    # in case of merging/preservation issues elsewhere.
                    current_state, more_msgs = validate_and_correct_trip_data(current_state, sanitized_query)
                    current_state.setdefault("messages", []).extend(more_msgs)
            except Exception:
                # Do not raise for this best-effort calculation; fall through and let
                # the normal follow-up logic ask the question if calculation fails.
                pass

            return current_state

        if user_responses:
            ans = user_responses.pop(0)

            # 1. Apply the new answer and run local validation/correction (which calculates end_date)
            json_response = apply_answer(missing_field, ans, json_response)

            # CRITICAL FIX: After applying the answer, immediately restart the loop
            # to re-evaluate missing_fields and skip asking for the calculated end_date.
            continue

        else:
            # Non-interactive / API mode or no more answers: return 'awaiting_user_input' state
            question = questions.get(missing_field) or f"Please provide {missing_field}:"
            json_response["status"] = "awaiting_user_input"
            json_response.setdefault("messages", []).append({
                "type": "followup",
                "field": missing_field,
                "question": question,
            })
            return OrchestratorAgent4OutputSchema(**json_response)

    # Return the complete state
    return OrchestratorAgent4OutputSchema(**json_response)
