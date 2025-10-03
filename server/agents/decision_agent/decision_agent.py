import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from sympy.physics.units import temperature

from server.schemas.decision_agent_schema import AgentRouteDecision
from server.utils.config import GEMINI_API_KEY, GEMINI_MODEL

system_prompt = """
                You are the **Decision Agent** for a multi-agent trip planning system. 
                Your sole responsibility is to analyze the user's initial query and decide which specific agent should handle the request.
                The chat MUST be based on the travel domain and trip planning.
                **STRICTLY ONLY SUGGEST LOCATIONS IN SRI LANKA**. Avoid all international destinations.

                **Strict Instructions (MUST BE FOLLOWED):**
                1.  **Analyze the intent:** Determine the *primary* purpose of the user's request.
                2.  **Output via FUNCTION CALL:** You **MUST** call the `AgentRouteDecision` function *once* with the determined agent name. **DO NOT generate any text output.**
                3.  **Mapping:**
                    * **Friendly chat/General conversation:** `chat_agent`
                    * **Request to plan an entire trip/vacation/itinerary:** `orchestrator_agent`
                    * **Asking for destination ideas/places to visit:** `location_agent`
                    * **Asking for things to do/attractions in a specific place:** `activity_agent`
                    * **Asking for a packing list/what to bring:** `packing_agent`
                    * **User provides a URL (link) and asks to summarize it or ask a question from it:** `explorer_agent`
                """

def create_decision_agent():
    """
    Creates the LangChain runnable for the Decision Agent using the Gemini API.
    """
    llm=ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0, api_key=GEMINI_API_KEY)

    prompt=ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{user_query}")
        ]
    )

    decision_chain=(
        prompt
        | llm.bind_tools(tools=[AgentRouteDecision])
    )

    return decision_chain

def decision_agent_node(state: dict) -> dict:
    decision_chain=create_decision_agent()
    user_query=state["user_query"]

    response=decision_chain.invoke({"user_query": user_query})

    print(f"DEBUG: Raw Model Response: {response}")

    # Check if a tool call was actually returned
    if not response.tool_calls:
        # If the model didn't call the function, this is a failure
        print("Model failed to call the AgentRouteDecision function.")
        state["intent"] = "chat_agent" # Fallback
        return state

    tool_call=response.tool_calls[0]

    # **FIXED LINE HERE:** Accessing 'next_agent' instead of 'next_agent_name'
    next_agent_name = tool_call['args'].get('next_agent')

    print(f"Next agent name: {next_agent_name}")

    state["intent"] = next_agent_name
    return state

# if __name__== "__main__":
#     # For testing purposes
#     # test_state = {"user_query": "What are the best things to do in Galle?"}
#     test_state = {"user_query": "What are the best place to visit in sri lanka?"}
#     updated_state = decision_agent_node(test_state)
#     print(updated_state)
#
# Output:
# (.venv) PS C:\Users\dulha\GitHub\Seasonal_Travel_Recommender> python -m server.agents.decision_agent.decision_agent
# WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
# E0000 00:00:1759318314.355036   21352 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
# DEBUG: Raw Model Response: content='' additional_kwargs={'function_call': {'name': 'AgentRouteDecision', 'arguments': '{"next_agent": "location_agent"}'}} response_metadata={'promp
# t_feedback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.5-flash', 'safety_ratings': []} id='run--6240d46b-6cb8-4c9e-8930-6330d6cb16
# 5b-0' tool_calls=[{'name': 'AgentRouteDecision', 'args': {'next_agent': 'location_agent'}, 'id': 'edb82040-ae3a-429a-bd39-3b1b3db25e43', 'type': 'tool_call'}] usage_metadata={'input_tokens': 372, 'output_tokens': 63, 'total_tokens': 435, 'input_token_details': {'cache_read': 0}, 'output_token_details': {'reasoning': 44}}
# Next agent name: location_agent
# {'user_query': 'What are the best place to visit in sri lanka?', 'intent': 'location_agent'}