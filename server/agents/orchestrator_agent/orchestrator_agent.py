from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.schema import HumanMessage, AIMessage
from langchain_core.exceptions import OutputParserException
from langchain.chains import LLMChain
import json
from json import JSONDecodeError


from server.agents.orchestrator_agent.retriever import retrieve_relevant_context
from server.utils.config import OPENAI_API_KEY, LLM_MODEL
from server.schemas.orchestrator_schemas import (
    OrchestratorAgent4OutpuSchema,
    OrchestratorAgent4InputSchema,
)
from server.agents.orchestrator_agent.security import sanitize_input

# Initialize LLM and parser
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=LLM_MODEL, temperature=0)
parser = PydanticOutputParser(pydantic_object=OrchestratorAgent4OutpuSchema)

# Prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful assistant. You help peoples to get best recommendations to their travels in Sri Lanka. Extract the following information from the user's trip request:
        Do not include natural language, explanations, or any text outside of the JSON.
        - **destination**: The destination city (e.g., Paris, Tokyo, Galle).
        - **start_date**: The start date of the trip in YYYY-MM-DD format (if provided).
        - **end_date**: The end date of the trip in YYYY-MM-DD format (if provided).
        - **no_of_traveler**: The number of travelers (integer, if provided).
        - **season**: The season for the trip (e.g., summer, winter, spring, fall) or get the season based on start and end dates.
        - **budget**: The budget (low budget, high budget like wise).
        - **user_preferences**: Any specific preferences mentioned by the user (e.g., beach, mountains, culture).
        - **type_of_trip**: The type of trip (e.g., leisure, business, adventure, family).
        If information is not explicitly provided, ask friendly questions from the user and gather the information.
        Respond with a JSON object containing these keys.
        Example: {{"destination": "Paris", "start_date": "2025-09-06", "end_date": "2025-09-08", "no_of_traveler": 4, "budget": "medium", "user_preferences": ["culture", "food"], "type_of_trip": "leisure"}}
        Wrap the output in this format and provide no other text\n{format_instructions}""",
        ),
        ("system", "Ensure the JSON is correctly formatted."),
        (
            "system",
            "Make sure to validate the dates and ensure they are in the correct format.",
        ),
        (
            "system",
            "If the user provides ambiguous information, ask clarifying questions.",
        ),
        (
            "system",
            "If the user does not provide certain details, use 'None' or an empty list as appropriate.",
        ),
        (
            "system",
            "Always respond with a JSON object, even if some fields are None or empty.",
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{user_input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

# Create agent
agent = create_tool_calling_agent(llm=llm, tools=[], prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=[], verbose=True)
# agent_executor = LLMChain(llm=llm, prompt=prompt, verbose=True)

# Mandatory fields and follow-up questions
MANDATORY_FIELDS = [
    "destination",
    "start_date",
    "end_date",
    "no_of_traveler",
    "type_of_trip",
]
FOLLOWUP_QUESTIONS = {
    "destination": "🌍 Where would you like to travel?",
    "season": "🍂 Which season are you planning this trip for?",
    "start_date": "📅 What is your trip start date? (YYYY-MM-DD)",
    "end_date": "📅 What is your trip end date? (YYYY-MM-DD)",
    "no_of_traveler": "👥 How many people are traveling?",
    "budget": "💰 What is your budget (low, medium, high)?",
    "type_of_trip": "🎯 What type of trip is this (leisure, adventure, business, etc.)?",
}


def safe_parse(output_parser, text: str, prev_response=None):
    try:
        return output_parser.parse(text)
    except OutputParserException:
        # Fallback: keep old values if available
        fallback = {
            "destination": None,
            "season": None,
            "start_date": None,
            "end_date": None,
            "preferences": [],
            "no_of_traveler": None,
            "budget": None,
            "user_preferences": [],
            "type_of_trip": None,
            "additional_info": None,
            "status": "awaiting_user_input",
            "messages": [],
        }
        if prev_response:
            for k, v in prev_response.dict().items():
                if v not in (None, "", [], 0):
                    fallback[k] = v
        return output_parser.parse(json.dumps(fallback))


def run_llm_agent(
    state: OrchestratorAgent4InputSchema,
    chat_history: list = None,
    only_missing: list = None,
):
    if chat_history is None:
        chat_history = []

    print(f"\nDEBUG: sanitized input: {state.query}\n")
    sanitized_query = sanitize_input(state.query)

    if only_missing:
        sanitized_query = (
            f"User already provided some info. Still need: {', '.join(only_missing)}"
        )

    human_msg = HumanMessage(content=sanitized_query)
    chat_history.append(human_msg)

    result = agent_executor.invoke(
        {"user_input": sanitized_query, "chat_history": chat_history}
    )

    result_content = (
        result["output"]
        if isinstance(result, dict) and "output" in result
        else str(result)
    )

    chat_history.append(AIMessage(content=result_content))

    response = safe_parse(parser, result_content)
    return response, chat_history


# def call_orchestrator_agent(state: OrchestratorAgent4InputSchema, user_responses=None):
#     if user_responses is None:
#         user_responses = []

#     chat_history = []

#     # Step 1: Let LLM fill as much as possible
#     response, chat_history = run_llm_agent(state, chat_history)
#     response = OrchestratorAgent4OutpuSchema(**response.dict())

#     # Initialize json_response BEFORE the loop
#     try:
#         json_response = json.loads(response.json())
#     except (json.JSONDecodeError, AttributeError):
#         json_response = {
#             "location": response.location,
#             "start_date": response.start_date,
#             "end_date": response.end_date,
#             "no_of_traveler": response.no_of_traveler,
#             "type_of_trip": response.type_of_trip,
#             "status": response.status,
#             "preferences": [],
#             "additional_info": None,
#             "messages": [],
#         }

#     # Step 2: Only ask if mandatory fields missing
#     while True:
#         missing_fields = [f for f in MANDATORY_FIELDS if getattr(response, f) in (None, "", [], 0)]
#         print("DEBUG missing fields:", missing_fields)

#         if not missing_fields:
#             response.status = "complete"
#             json_response["status"] = response.status
#             break

#         missing_field = missing_fields[0]
#         question = FOLLOWUP_QUESTIONS[missing_field]

#         if user_responses:
#             answer = user_responses.pop(0)
#         else:
#             answer = input(question + " ")

#         if missing_field == "no_of_traveler":
#             response.no_of_traveler = int(answer)
#         elif missing_field in ["user_preferences", "preferences"]:
#             response.user_preferences = [x.strip() for x in answer.split(",")]
#         else:
#             setattr(response, missing_field, answer)

#         # Update json_response with latest values
#         json_response.update({
#             "location": response.location,
#             "start_date": response.start_date,
#             "end_date": response.end_date,
#             "no_of_traveler": response.no_of_traveler,
#             "type_of_trip": response.type_of_trip,
#             "status": response.status,
#             "user_preferences": response.user_preferences,
#         })

#     return json_response


def call_orchestrator_agent(state: OrchestratorAgent4InputSchema, user_responses=None):
    if user_responses is None:
        user_responses = []

    chat_history = []

    # Step 1: Let LLM fill as much as possible
    response, chat_history = run_llm_agent(state, chat_history)
    response = OrchestratorAgent4OutpuSchema(**response.dict())

    # Initialize json_response
    try:
        json_response = json.loads(response.json())
    except (json.JSONDecodeError, AttributeError):
        json_response = {
            "destination": response.destination,
            "start_date": response.start_date,
            "end_date": response.end_date,
            "no_of_traveler": response.no_of_traveler,
            "type_of_trip": response.type_of_trip,
            "status": response.status,
            "preferences": [],
            "additional_info": None,
            "messages": [],
        }

    # Step 2: Only ask if mandatory fields missing
    while True:
        missing_fields = [
            f for f in MANDATORY_FIELDS if getattr(response, f) in (None, "", [], 0)
        ]
        print("DEBUG missing fields:", missing_fields)

        if not missing_fields:
            response.status = "complete"
            json_response["status"] = response.status
            break

        missing_field = missing_fields[0]
        question = FOLLOWUP_QUESTIONS[missing_field]

        if user_responses:
            answer = user_responses.pop(0)
        else:
            answer = input(question + " ")

        if missing_field == "no_of_traveler":
            response.no_of_traveler = int(answer)
        elif missing_field in ["user_preferences", "preferences"]:
            response.user_preferences = [x.strip() for x in answer.split(",")]
        else:
            setattr(response, missing_field, answer)

        # Update json_response with latest values
        json_response.update(
            {
                "destination": response.destination,
                "start_date": response.start_date,
                "end_date": response.end_date,
                "no_of_traveler": response.no_of_traveler,
                "type_of_trip": response.type_of_trip,
                "status": response.status,
                "user_preferences": response.user_preferences,
            }
        )

    return json_response
