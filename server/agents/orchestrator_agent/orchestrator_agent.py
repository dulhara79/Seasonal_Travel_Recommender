import os
import json
from json import JSONDecodeError
from datetime import datetime, date

# LangChain Imports
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.schema import HumanMessage, AIMessage
from langchain_core.exceptions import OutputParserException
from langchain.chains import LLMChain

# Local Imports
# NOTE: Ensure these imports are correctly set up in your environment
from server.agents.orchestrator_agent.retriever import retrieve_relevant_context
from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from server.schemas.orchestrator_schemas import (
    OrchestratorAgent4OutpuSchema,
    OrchestratorAgent4InputSchema,
)
from server.agents.orchestrator_agent.security import sanitize_input

# --- 1. INITIALIZATION & HELPER FUNCTIONS ---

# Get the current date to prevent future dates from being predicted
CURRENT_DATE_STR = datetime.now().strftime("%Y-%m-%d")
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.3)
parser = PydanticOutputParser(pydantic_object=OrchestratorAgent4OutpuSchema)

# Sri Lankan Seasons for external enforcement
SRI_LANKA_SEASONS = {
    range(5, 10): "Southwest Monsoon",   # May (5) to Sept (9)
    tuple(list(range(10, 13)) + [1]): "Northeast Monsoon",  # Oct (10), Nov (11), Dec (12), Jan (1)
    range(2, 5): "Inter-monsoon",        # Feb (2) to April (4)
}



def get_sri_lanka_season(date_str: str) -> str | None:
    """Infers the Sri Lankan season from a YYYY-MM-DD date string."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month = dt.month
        for month_range, season in SRI_LANKA_SEASONS.items():
            if isinstance(month_range, range) and month in month_range:
                return season
            if isinstance(month_range, tuple) and month in month_range:
                return season
        return None
    except:
        return None


# --- 2. EXTRACTION PROMPT & AGENT (FIXED LOGIC) ---

extraction_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            f"""
            You are a helpful assistant that extracts structured trip details for travel planning in **Sri Lanka only**. 
            The **CURRENT DATE is {CURRENT_DATE_STR}**.
            Follow these rules strictly:

            1. **Destination Validation:**
               - Only accept **Sri Lankan destinations**. 
               - If a foreign location is mentioned, set `"destination": null`.

            2. **Date Validation:**
               - Dates must be in `YYYY-MM-DD` format and **must be in the future (after {CURRENT_DATE_STR})**.  
               - If only one date is provided, set the other to `null`.  
               - If the date is invalid or in the past (before or on {CURRENT_DATE_STR}), set it to `null`.  
               - Do NOT guess dates.

            3. **Travelers Validation:**
               - Extract as an integer. If not provided, set `"no_of_traveler": null`.

            4. **Season (For LLM only):**
               - If dates are given, infer the season based on Sri Lanka’s climate (May–Sept: SW Monsoon, Oct–Jan: NE Monsoon, Feb–April: Inter-monsoon).
               - If no date is given, set `"season": null`.

            5. **Budget:**
               - Extract only if explicitly stated (e.g., low, medium, high, luxury). Otherwise set `"budget": null`.

            6. **Preferences & Type of Trip:**
               - Extract any mentioned preferences (e.g., beaches, culture, history) as a list. If none provided, use an empty list `[]`.  
               - Extract type of trip (e.g., family, honeymoon, leisure). Otherwise set `"type_of_trip": null`.

            7. **Output Format:**
               - Always respond ONLY with a **single valid JSON object**. No natural language, no extra text.

            Example Valid Output:
            {{
              "destination": "Galle",
              "start_date": "2026-09-06",
              "end_date": "2026-09-08",
              "no_of_traveler": 4,
              "season": "Southwest Monsoon",
              "budget": "medium",
              "user_preferences": ["culture", "food"],
              "type_of_trip": "leisure"
            }}
            """.replace("{", "{{").replace("}", "}}"),
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

# --- 4. CORE FUNCTIONS ---

# UPDATED: Added 'user_preferences' to mandatory fields
MANDATORY_FIELDS = [
    "destination",
    "start_date",
    "end_date",
    "no_of_traveler",
    "type_of_trip",
    "user_preferences",
]


def create_followup_questions(json_response: dict, missing_fields: list) -> dict:
    """
    Uses the LLM to generate a single, creative, context-aware question
    for the most critical missing mandatory field.
    """
    if not missing_fields:
        return {}

    missing_field = missing_fields[0]

    # Generate the question using the LLM
    question_result = question_generator_chain.invoke({
        "current_data": json.dumps(json_response, indent=2),
        "missing_field": missing_field
    })

    question_text = question_result.get('text', f"Please provide the missing information for {missing_field}:").strip()

    return {missing_field: question_text}


def safe_parse(output_parser, text: str, prev_response=None):
    """Safely parse LLM output."""
    # ... (safe_parse logic remains the same for robustness)
    try:
        return output_parser.parse(text)
    except OutputParserException as e:
        print(f"OutputParserException caught: {e}")
        fallback = {
            "destination": None, "season": None, "start_date": None, "end_date": None,
            "no_of_traveler": None, "budget": None, "user_preferences": [],
            "type_of_trip": None, "additional_info": None, "status": "awaiting_user_input", "messages": [],
        }
        if prev_response:
            for k, v in prev_response.dict().items():
                if v not in (None, "", [], 0) and k in fallback:
                    fallback[k] = v
        try:
            return output_parser.parse(json.dumps(fallback))
        except Exception:
            print("ERROR: Failed to parse fallback structure.")
            raise


def run_llm_agent(
        state: OrchestratorAgent4InputSchema,
        chat_history: list = None,
        prev_response_pydantic=None
):
    """Executes the core extraction agent and applies post-extraction validation/correction."""
    if chat_history is None:
        chat_history = []

    sanitized_query = sanitize_input(state.query)

    result = agent_executor.invoke(
        {"user_input": sanitized_query, "chat_history": chat_history}
    )

    result_content = result.get("output", str(result))
    response_pydantic = safe_parse(parser, result_content, prev_response=prev_response_pydantic)
    json_response = response_pydantic.dict()

    # --- POST-EXTRACTION VALIDATION AND CORRECTION ---

    # 1. Correct Past/Invalid Dates and Infer Season
    current_date = datetime.now().date()

    for key in ["start_date", "end_date"]:
        date_str = json_response.get(key)
        if date_str:
            try:
                extracted_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if extracted_date <= current_date:
                    # Date is in the past or today, set to null to force asking again
                    print(f"DEBUG: Setting {key} to null (Past Date: {date_str})")
                    json_response[key] = None
            except ValueError:
                # Invalid date format
                print(f"DEBUG: Setting {key} to null (Invalid Date Format: {date_str})")
                json_response[key] = None

    # 2. Enforce Season Inference (as LLM often misses this in the JSON output)
    if json_response.get("start_date") and json_response.get("season") is None:
        season = get_sri_lanka_season(json_response["start_date"])
        if season:
            json_response["season"] = season
            print(f"DEBUG: Overriding season based on start_date: {season}")

    # Re-convert to Pydantic for final consistent output
    return OrchestratorAgent4OutpuSchema(**json_response)


# --- 5. MAIN ORCHESTRATOR FUNCTION (Logic remains the same) ---

def call_orchestrator_agent(state: OrchestratorAgent4InputSchema, user_responses: list = None, prev_json_response: dict = None):
    """
    Main function for the orchestrator, handles initial extraction and follow-up
    questions for mandatory fields.
    """
    if user_responses is None:
        user_responses = []
    # If a previous partial state is provided, resume from it. Otherwise run
    # the LLM extractor to create an initial json_response.
    if prev_json_response:
        # Work on a shallow copy to avoid mutating caller data
        json_response = prev_json_response.copy()
    else:
        # Step 1: Let LLM fill as much as possible from the initial query
        response_pydantic = run_llm_agent(state)
        print("DEBUG: Orchestrator Agent RAW LLM Extraction:", response_pydantic)
        # Convert the pydantic object to a mutable dict for easier manipulation
        json_response = response_pydantic.dict()


    # Step 2: Only ask if mandatory fields are missing
    while True:
        # Check against the updated MANDATORY_FIELDS list
        missing_fields = [
            f for f in MANDATORY_FIELDS if (f == "user_preferences" and not json_response.get(f)) or (
                        f != "user_preferences" and json_response.get(f) in (None, "", 0))
        ]

        # Note: Added a special check for 'user_preferences' as it is a list,
        # checking if it's empty (not just None).

        print("DEBUG missing fields:", missing_fields)

        if not missing_fields:
            json_response["status"] = "complete"
            break

        missing_field = missing_fields[0]

        # --- Use the LLM to generate the creative question ---
        questions = create_followup_questions(json_response, missing_fields)

        # Helper to apply answer to response
        def apply_answer(field: str, ans: str):
            if field == "no_of_traveler":
                try:
                    json_response[field] = int(ans)
                except Exception:
                    pass
            elif field == "user_preferences":
                # Convert comma-separated string to list
                json_response["user_preferences"] = [x.strip() for x in ans.split(",") if x.strip()]
            else:
                json_response[field] = ans.strip()

            # Re-run post-processing after getting a new answer (important for dates/season)
            if field in ["start_date", "end_date"]:
                # This logic is a simplified version of re-running the agent's internal validation
                # A full LangGraph/state machine would handle this more cleanly.

                # Check for past/invalid date again
                if json_response.get(field):
                    try:
                        extracted_date = datetime.strptime(json_response[field], "%Y-%m-%d").date()
                        if extracted_date <= datetime.now().date():
                            print(f"DEBUG: User input for {field} was a past date. Setting to null.")
                            json_response[field] = None
                    except ValueError:
                        print(f"DEBUG: User input for {field} was invalid format. Setting to null.")
                        json_response[field] = None

                # Update season if start_date is now valid
                if json_response.get("start_date") and json_response.get("season") is None:
                    season = get_sri_lanka_season(json_response["start_date"])
                    if season:
                        json_response["season"] = season
                        print(f"DEBUG: Auto-updated season to {season} after date input.")

        if user_responses:
            # Non-interactive / resumed mode: pop answer from supplied list (frontend will pass the user's answer)
            ans = user_responses.pop(0)
            print(f"DEBUG: Auto-applying answer for '{missing_field}': '{ans}'")
            apply_answer(missing_field, ans)
        else:
            # Non-interactive / API mode: do NOT block on input(). Instead,
            # return an 'awaiting_user_input' state including the generated
            # follow-up question so the frontend can present it to the user
            # and resume the flow.

            # Get the specific question generated by the LLM
            question = questions.get(missing_field) or f"Please provide {missing_field}:"

            # Mark state as awaiting user input and include a structured message
            json_response["status"] = "awaiting_user_input"
            json_response.setdefault("messages", [])
            json_response["messages"].append({
                "type": "followup",
                "field": missing_field,
                "question": question,
            })

            # Return the partial response so the API layer can send it back to client
            return OrchestratorAgent4OutpuSchema(**json_response)

        # Loop continues to check the state and ask for the next missing field

    # Return the complete state
    # return json_response
    return OrchestratorAgent4OutpuSchema(**json_response)

#
# if __name__ == "__main__":
#     # --- INTERACTIVE TEST RUN ---
#
#     # 1. Initial State (User query)
#     initial_state = OrchestratorAgent4InputSchema(
#         # The query mentions August, which is in the past (2025-10-01).
#         # The new logic will detect and nullify the predicted date, forcing an ask.
#         query="I want to plan an amazing trip for my family of four next summer. We love the beach and mountains.",
#         status="initial"
#     )
#
#     # 2. Simulate User Responses for missing mandatory fields (for non-interactive testing)
#     simulated_answers = [
#         "Jaffna",  # destination
#         "2026-07-15",  # start_date
#         "2026-07-28",  # end_date
#         "leisure",  # type_of_trip
#         "food, culture",  # user_preferences (now mandatory)
#     ]
#
#     print("--- ORCHESTRATOR AGENT START ---")
#
#     # Run the orchestrator with simulated answers for a non-interactive test
#     # Change 'user_responses=simulated_answers' to 'user_responses=None' for console input
#     # final_state = call_orchestrator_agent(initial_state, user_responses=simulated_answers)
#     final_state = call_orchestrator_agent(initial_state, user_responses=None)
#
#     print("\n--- FINAL ORCHESTRATOR OUTPUT ---")
#     print(json.dumps(final_state, indent=4))
#     print("-----------------------------------")
#