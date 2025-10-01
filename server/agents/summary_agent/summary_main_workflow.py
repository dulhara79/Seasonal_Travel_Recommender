#
# main_workflow.py (Conceptual - requires external dependencies like LangGraph/Pydantic for full implementation)
# # This is a conceptual outline of how you might structure the main workflow for the Summary Agent.

from server.schemas.summary_schemas import SummaryAgentInputSchema
from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL
from server.agents.summary_agent.summary_refiner import refine_summary, get_summary_refinement_chain
from server.agents.summary_agent.summary_agent import generate_summary,_get_summary_llm  # Your main function


# --- State Structure (Concept) ---
class ConversationState:
    """The central state object for the entire conversation."""

    def __init__(self, trip_data: SummaryAgentInputSchema, latest_summary_text: str = ""):
        self.trip_data = trip_data
        self.latest_summary_text = latest_summary_text
        # Status helps the workflow determine if a summary is already present
        self.status = "planning" if not latest_summary_text else "summary_generated"


# --- 1. INTENT CLASSIFIER CHAIN (The Router) ---

def classify_intent(user_query: str) -> str:
    """Uses LLM to classify user intent: EDIT_SUMMARY or EDIT_TRIP_DATA."""
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_openai import ChatOpenAI

        # Use a very low temperature for reliable classification
        llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.0)

        CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages([
            ("system",
             "You are a routing agent. Classify the user's request. Respond with ONLY the category name."
             "Categories: 'EDIT_SUMMARY' (if asking to change tone/length/style of the document),"
             " or 'EDIT_TRIP_DATA' (if asking to change a fact like date, destination, budget, or count)."
             ),
            ("human", "User message: {query}")
        ])

        chain = CLASSIFIER_PROMPT | llm | StrOutputParser()
        intent = chain.invoke({"query": user_query}).strip().upper()

        # Simple validation
        if intent not in ['EDIT_SUMMARY', 'EDIT_TRIP_DATA']:
            return 'EDIT_TRIP_DATA'  # Default to data change if classification is poor
        return intent

    except Exception as e:
        print(f"Intent classification failed: {e}")
        return 'EDIT_TRIP_DATA'  # Safe fallback


# --- 2. THE MAIN CONVERSATIONAL LOOP ---

def process_conversation_step(state: ConversationState, user_input: str) -> ConversationState:
    """Handles routing based on intent."""

    # 1. If no summary exists, run the full planning cycle
    if not state.latest_summary_text:
        # NOTE: This step is where your full Orchestrator/Planning Agents would run
        # For this example, we just assume it updates trip_data and generates the first summary
        # (This is where you would call generate_summary for the first time)

        # Placeholder for full planning cycle:
        updated_trip_data = run_orchestrator_to_update_data(state.trip_data, user_input)
        final_summary_output = generate_summary(updated_trip_data)

        state.trip_data = updated_trip_data
        state.latest_summary_text = final_summary_output.summary
        state.status = "summary_generated"
        print(f"ASSISTANT: First summary created:\n{state.latest_summary_text}")
        return state

    # 2. Summary exists: Classify the new user input
    intent = classify_intent(user_input)
    print(f"DEBUG: Classified intent as: {intent}")

    if intent == 'EDIT_SUMMARY':
        # Route 1: Summary Refinement
        new_summary = refine_summary(
            previous_summary=state.latest_summary_text,
            user_feedback=user_input,
            api_key=OPENAI_API_KEY,
            model_name=OPENAI_MODEL
        )
        state.latest_summary_text = new_summary
        state.status = "refining"
        print(f"ASSISTANT: Summary refined based on style:\n{state.latest_summary_text}")

    elif intent == 'EDIT_TRIP_DATA':
        # Route 2: Trip Data Update (Forces full summary regeneration)

        # NOTE: This is where you would call your existing Orchestrator/Planning agents
        # to process the factual change and update state.trip_data
        updated_trip_data = run_orchestrator_to_update_data(state.trip_data, user_input)

        # Regenerate the entire summary using the original generate_summary function
        final_summary_output = generate_summary(updated_trip_data)

        state.trip_data = updated_trip_data
        state.latest_summary_text = final_summary_output.summary
        state.status = "summary_generated"
        print(f"ASSISTANT: Trip data updated and summary regenerated:\n{state.latest_summary_text}")

    return state


# --- Placeholder function for your existing planning logic ---
def run_orchestrator_to_update_data(current_data: SummaryAgentInputSchema, query: str) -> SummaryAgentInputSchema:
    """Simulates updating the structured trip data based on a user query."""
    print(f"INFO: Running Orchestrator to process factual change: '{query}'")
    # In a real system, this agent would update fields like destination, dates, etc.
    # For simplicity, we just return the current data
    return current_data
