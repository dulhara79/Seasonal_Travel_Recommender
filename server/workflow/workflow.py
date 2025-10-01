# workflow.py

import os
from typing import Optional

from langgraph.graph import StateGraph, END
from server.workflow.app_state import TripPlanState
from server.workflow.agent_nodes import (
    route_user_query,
    chat_node,
    orchestrator_node,
    location_node,
    _run_activity_agent,  # Reusing simple functions for full chain
    _run_packing_agent,
    summary_node,
    refiner_node,
    simple_location_node,
    simple_activity_node,
    simple_packing_node
)
from server.schemas.orchestrator_schemas import OrchestratorAgent4OutpuSchema


# --- 1. Graph Definition ---
def build_trip_workflow():
    """Builds the complete LangGraph workflow."""

    workflow = StateGraph(TripPlanState)

    # --- 2. Define Nodes ---
    workflow.add_node("router", route_user_query)
    workflow.add_node("chat_agent", chat_node)
    workflow.add_node("orchestrator_agent", orchestrator_node)

    # Full Planning Chain Nodes
    workflow.add_node("location_agent", location_node)
    workflow.add_node("activity_agent", _run_activity_agent)
    workflow.add_node("packing_agent", _run_packing_agent)
    workflow.add_node("summary_agent", summary_node)

    # Simple, Single-Shot Agents
    workflow.add_node("simple_location", simple_location_node)
    workflow.add_node("simple_activity", simple_activity_node)
    workflow.add_node("simple_packing", simple_packing_node)

    # Summary Refiner Node
    workflow.add_node("refine_summary", refiner_node)

    # --- 3. Define Edges and Conditionals ---

    # Entry Point
    workflow.set_entry_point("router")

    # The Router's Conditional Edges (The Core Decision Logic)
    workflow.add_conditional_edges(
        "router",
        # Logic is in route_user_query to return the next node name
        # lambda state: state["intent"],
        # {
        #     "chat_agent": "chat_agent",  # Path 1: General Chat
        #     "orchestrator_agent": "orchestrator_agent",  # Path 2: Full Planning
        #     "location_agent": "simple_location",  # Path 3: Single-Shot Location Query
        #     "activity_agent": "simple_activity",  # Path 3: Single-Shot Activity Query
        #     "packing_agent": "simple_packing",  # Path 3: Single-Shot Packing Query
        #     "refine_summary": "refine_summary",  # Path 4: Summary Editing
        # }
        lambda state: state["intent"],
        {
            "chat_agent": "chat_agent",  # Path 1: General Chat
            "orchestrator_agent": "orchestrator_agent",  # Path 2: Full Planning
            "location_agent": "chat_agent",  # Path 3: Single-Shot Location Query
            "activity_agent": "chat_agent",  # Path 3: Single-Shot Activity Query
            "packing_agent": "chat_agent",  # Path 3: Single-Shot Packing Query
            "refine_summary": "refine_summary",  # Path 4: Summary Editing
        }
    )

    # --- Full Planning Chain Edges (Orchestrator -> ...) ---
    workflow.add_conditional_edges(
        "orchestrator_agent",
        # FIX: Access the 'status' field using dot notation (.status) since state["trip_data"] is a Pydantic object.
        lambda state: (
            "continue_planning"
            if state["trip_data"] and state["trip_data"].status == 'complete'
            else "await_input"
        ),
        {
            "continue_planning": "location_agent",
            "await_input": END
        }
    )

    # Full Planning Chain (Sequential Execution)
    workflow.add_edge("location_agent", "activity_agent")
    workflow.add_edge("activity_agent", "packing_agent")
    workflow.add_edge("packing_agent", "summary_agent")

    # --- Termination Edges ---
    workflow.add_edge("chat_agent", END)
    workflow.add_edge("summary_agent", END)
    workflow.add_edge("refine_summary", END)
    workflow.add_edge("simple_location", END)
    workflow.add_edge("simple_activity", END)
    workflow.add_edge("simple_packing", END)

    return workflow.compile()


# --- 4. Execution Logic ---
if __name__ == "__main__":
    # Initialize the graph
    app = build_trip_workflow()

    print("--- Trip Planning Assistant Initialized ---")


    # Sample run function
    def run_conversation(query: str, state: Optional[TripPlanState] = None) -> TripPlanState:

        # If no state is provided, initialize a new one
        if state is None:
            state = {
                "user_query": query,
                "chat_history": [],
                "intent": None,
                # FIX 1: Store the Pydantic object instance, not its dictionary representation.
                # Use .model_dump() for dictionary conversion if needed elsewhere (like state.update).
                "trip_data": OrchestratorAgent4OutpuSchema(),
                "location_recs": None,
                "activity_recs": None,
                "packing_recs": None,
                "latest_summary": None,
                "final_response": None
            }
        else:
            # Update state with the new query
            state['user_query'] = query
            state['chat_history'].append(("human", query))

        # The LangGraph is run with the current state as input
        for step_output in app.stream(state):
            # The last key in the dict indicates the final node executed
            last_node = list(step_output.keys())[-1]
            state.update(step_output[last_node])  # Update the state with the node's output

        # Add the final response to the chat history for context
        if state.get("final_response"):
            state['chat_history'].append(("ai", state["final_response"]))

        return state


    print("\n\n--- DEMO ---")
    state = run_conversation(
        "What are the best locations to visit in Sri Lanka in late October for a family of four who love the beach and mountains?")
    print(f"ASSISTANT: {state['final_response']}")

    # # --- INTERACTIVE DEMO ---
    #
    # # 1. Start a conversation (triggers full planning)
    # print("\n\n--- DEMO 1: Initiate Planning ---")
    # state = run_conversation(
    #     "I want to plan an amazing trip for my family of four next summer. We love the beach and mountains.")
    # print(f"ASSISTANT: {state['final_response']}")
    #
    # # 2. User provides missing info (Destination)
    # print("\n\n--- DEMO 2: Provide Answer 1 (Destination) ---")
    # state = run_conversation("We want to go to Galle.", state)
    # print(f"ASSISTANT: {state['final_response']}")
    #
    # # 3. User provides another answer (Dates)
    # print("\n\n--- DEMO 3: Provide Answer 2 (Dates) ---")
    # state = run_conversation("We'll go from 2026-07-15 to 2026-07-28.", state)
    # print(f"ASSISTANT: {state['final_response']}")
    #
    # # 4. User provides the final missing pieces (This should complete the plan and trigger the full chain: Location -> Activity -> Packing -> Summary)
    # print("\n\n--- DEMO 4: Complete Data & Generate Plan ---")
    # # This query might be rerouted by the decision agent, so we make it simple
    # state = run_conversation("This is a leisure trip with a medium budget.", state)
    # print(f"ASSISTANT: \n{state['final_response']}")
    #
    # # 5. User refines the summary (Triggers Refiner Agent)
    # print("\n\n--- DEMO 5: Refine Summary (Refiner Agent) ---")
    # state = run_conversation("Make the summary shorter and add emojis to the section headings.", state)
    # print(f"ASSISTANT: \n{state['final_response']}")

####---------------OUTPUT SAMPLE---------------####
# Windows PowerShell
# Copyright (C) Microsoft Corporation. All rights reserved.
#
# Install the latest PowerShell for new features and improvements! https://aka.ms/PSWindows
#
# (.venv) PS C:\Users\dulha\GitHub\Seasonal_Travel_Recommender> python -m server.workflow.workflow
# C:\Users\dulha\GitHub\Seasonal_Travel_Recommender\server\agents\orchestrator_agent\vector_store.py:12: LangChainDeprecationWarning: The class `Chroma` was deprecated in LangChain 0.2.9 and will be removed in 1.0. An updated version of the class exists in the :class:`~langchain-chroma package and should be used instead. To use it run `pip install -U :class:`~langchain-chroma` and import as `from :class:`~langchain_chroma import Chroma``.
#   vectorstore = Chroma(
# Chroma persisted at: data/orchestrator_chroma
# ['chroma.sqlite3', 'da9066f9-d534-41fc-8b2f-d0d17cb9bb39']
# Current working directory: C:\Users\dulha\GitHub\Seasonal_Travel_Recommender
# ChromaDB path: C:\Users\dulha\GitHub\Seasonal_Travel_Recommender\chroma_db
# C:\Users\dulha\GitHub\Seasonal_Travel_Recommender\server\agents\orchestrator_agent\orchestrator_agent.py:136: LangChainDeprecationWarning: The class `LLMChain` was deprecated in LangChain 0.1.17 and will be removed in 1.0. Use :meth:`~RunnableSequence, e.g., `prompt | llm`` instead.
#   question_generator_chain = LLMChain(llm=llm, prompt=QUESTION_PROMPT, verbose=False)
# --- Trip Planning Assistant Initialized ---
#
#
# --- DEMO 1: Initiate Planning ---
# --- ROUTER: Classifying user intent for: I want to plan an amazing trip for my family of fo...
# WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
# E0000 00:00:1759342009.925383   22572 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
# DEBUG: Raw Model Response: content='' additional_kwargs={'function_call': {'name': 'AgentRouteDecision', 'arguments': '{"next_agent": "orchestrator_agent"}'}} response_metadata={'prompt_feedback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.5-flash', 'safety_ratings': []} id='run--10bba100-fec1-445e-be2e-2b73874994b7-0' tool_calls=[{'name': 'AgentRouteDecision', 'args': {'next_agent': 'orchestrator_agent'}, 'id': 'cc6d2737-2f3d-4273-831b-b3508ef502cd', 'type': 'tool_call'}] usage_metadata={'input_tokens': 382, 'output_tokens': 81, 'total_tokens': 463, 'input_token_details': {'cache_read': 0}, 'output_token_details': {'reasoning': 60}}
# Next agent name: orchestrator_agent
# --- NODE: Orchestrator Agent Executing...
#
# Debug: Original input length: 98 characters, 20 words
#
#
# > Entering new AgentExecutor chain...
#
# Invoking: `extract_destination` with `{'text': 'beach and mountains'}`
#
#
# extract_destination is not a valid tool, try one of [].
# Invoking: `extract_preferences` with `{'text': 'beach and mountains, family'}`
#
#
# extract_preferences is not a valid tool, try one of [].{
#   "destination": null,
#   "start_date": null,
#   "end_date": null,
#   "no_of_traveler": 4,
#   "season": null,
#   "budget": null,
#   "user_preferences": ["beach", "mountains"],
#   "type_of_trip": "family"
# }
#
# > Finished chain.
# DEBUG: Orchestrator Agent RAW LLM Extraction: destination=None season=None start_date=None end_date=None user_preferences=['beach', 'mountains'] no_of_traveler=4 budget=None type_of_trip='family' additional_info=None status=None messages=[]
# DEBUG missing fields: ['destination', 'start_date', 'end_date']
#
# What specific destination in Sri Lanka are you interested in visiting? ➡️ Matara
# DEBUG missing fields: ['start_date', 'end_date']
#
# When are you planning to start your trip to Matara, Sri Lanka? ➡️ 2025-10-20
# DEBUG: Auto-updated season to Northeast Monsoon after date input.
# DEBUG missing fields: ['end_date']
#
# When do you plan to end your trip to Matara? ➡️ 2025-10-25
# DEBUG missing fields: []
# --- NODE: Location Agent Executing...
# [Comm Flow] User → LocationAgent → Gemini
# DEBUG: [LocationAgent] Parsed response: {'recommended_locations': [{'name': 'Polhena Beach', 'type': 'Beach', 'reason': 'Ideal for families during late October. The natural coral r
# eef creates calm, shallow waters perfect for children to swim and snorkel safely. While occasional inter-monsoon showers might occur, the weather is typically warm and sunny (aroun
# d 26-30°C), allowing for plenty of enjoyable beach time.'}, {'name': 'Mirissa Beach & Whale Watching', 'type': 'Adventure/Nature/Beach', 'reason': 'Late October marks the beginning
#  of the highly anticipated whale and dolphin watching season off Mirissa, making it an excellent time for a family adventure. The beautiful crescent-shaped beach is also perfect fo
# r relaxing and enjoying the warm, transitional weather, which typically features sunny periods with potential for brief afternoon showers.'}, {'name': 'Dondra Head Lighthouse', 'ty
# pe': 'Scenic', 'reason': 'As the southernmost point of Sri Lanka, this location offers breathtaking panoramic views of the Indian Ocean. Visiting in late October provides pleasant,
#  warm weather for exploration. While brief inter-monsoon showers are possible (average temperature 26-30°C), they usually clear quickly, allowing for stunning vistas and memorable
# family photos without being overly hot or crowded.'}, {'name': 'Weherahena Raja Maha Viharaya (Weherahena Temple)', 'type': 'Cultural/Scenic', 'reason': "This significant Buddhist
# temple, known for its massive Buddha statue and intricate cave temple, offers a rich cultural experience. It's suitable for a family visit in late October as cultural sites are enj
# oyable regardless of the weather. The slightly elevated location provides some scenic views of the surrounding area, and the warm, often sunny conditions are comfortable for exploring the temple grounds."}], 'status': 'complete', 'disclaimer': 'Recommendations are generated fairly and do not store personal user data.'}
# Executing Activity Agent: Generating activity plans...
# Executing Packing Agent: Generating packing list...
# --- NODE: Summary Agent Executing...
#
# DEBUG: Generating summary for state: {'destination': 'Matara', 'season': 'Northeast Monsoon', 'start_date': '2025-10-20', 'end_date': '2025-10-25', 'user_preferences': ['beach', 'm
# ountains'], 'no_of_traveler': 4, 'budget': None, 'type_of_trip': 'family', 'additional_info': None, 'status': 'completed', 'messages': [], 'location_recommendations': {'recommended
# _locations': [{'name': 'Polhena Beach', 'type': 'Beach', 'reason': 'Ideal for families during late October. The natural coral reef creates calm, shallow waters perfect for children
#  to swim and snorkel safely. While occasional inter-monsoon showers might occur, the weather is typically warm and sunny (around 26-30°C), allowing for plenty of enjoyable beach ti
# me.'}, {'name': 'Mirissa Beach & Whale Watching', 'type': 'Adventure/Nature/Beach', 'reason': 'Late October marks the beginning of the highly anticipated whale and dolphin watching
#  season off Mirissa, making it an excellent time for a family adventure. The beautiful crescent-shaped beach is also perfect for relaxing and enjoying the warm, transitional weathe
# r, which typically features sunny periods with potential for brief afternoon showers.'}, {'name': 'Dondra Head Lighthouse', 'type': 'Scenic', 'reason': 'As the southernmost point o
# f Sri Lanka, this location offers breathtaking panoramic views of the Indian Ocean. Visiting in late October provides pleasant, warm weather for exploration. While brief inter-mons
# oon showers are possible (average temperature 26-30°C), they usually clear quickly, allowing for stunning vistas and memorable family photos without being overly hot or crowded.'},
#  {'name': 'Weherahena Raja Maha Viharaya (Weherahena Temple)', 'type': 'Cultural/Scenic', 'reason': "This significant Buddhist temple, known for its massive Buddha statue and intri
# cate cave temple, offers a rich cultural experience. It's suitable for a family visit in late October as cultural sites are enjoyable regardless of the weather. The slightly elevat
# ed location provides some scenic views of the surrounding area, and the warm, often sunny conditions are comfortable for exploring the temple grounds."}], 'status': 'complete', 'di
# sclaimer': 'Recommendations are generated fairly and do not store personal user data.'}, 'activity_recommendations': {'day_plans': [{'date': '2026-07-16', 'suggestions': [{'title':
#  'Visit Sigiriya Rock', 'time_of_day': 'morning'}]}]}, 'packing_list': {'categories': [{'name': 'Essentials', 'items': [{'name': 'Sunscreen', 'reason': 'High UV index in Sri Lanka'}]}]}}
#
# DEBUG: Final polished summary: # 🎉 Your Custom Trip to Matara
#
# ## Quick Links
# - Dates & Season
# - Recommended Destinations
# - Packing Essentials
# - Responsible AI Notes
#
# ---
#
# ## Hello there! Your exciting trip to **Matara** is all set. Here's a creative overview of your personalized itinerary:
#
# ## 🗓️ Dates & Season
# - **Dates**: October 20, 2025, to October 25, 2025
# - **Duration**: October 20, 2025, to October 25, 2025
# - **Season**: Northeast Monsoon in Sri Lanka, great for North/East coast exploration
#
# ## 👥 Who's Traveling?
# - **Travelers**: 4 people
# - **Type**: Family trip
#
# ## 🎯 Your Vibe
# - **Interests**: Beach, Mountains
#
# ## 🗺️ Recommended Destinations
# 1. **Polhena Beach** (Beach)
#    - Ideal for families in late October
#    - Calm, shallow waters for safe swimming and snorkeling
#    - Warm and sunny weather (26-30°C)
#
# 2. **Mirissa Beach & Whale Watching** (Adventure/Nature/Beach)
#    - Whale and dolphin watching season starts in late October
#    - Relaxing beach with sunny periods and potential brief showers
#
# 3. **Dondra Head Lighthouse** (Scenic)
#    - Breathtaking views of the Indian Ocean
#    - Pleasant, warm weather for exploration
#
# 4. **Weherahena Raja Maha Viharaya (Weherahena Temple)** (Cultural/Scenic)
#    - Significant Buddhist temple with cultural richness
#    - Enjoyable visit regardless of weather
#
# ## 🎡 Daily Activities
# ### 📅 2026-07-16
# - **Morning**: Visit Sigiriya Rock
#
# ## 🎒 Suggested Packing List
# ### Essentials
# - Sunscreen (High UV index in Sri Lanka)
#
# ---
#
# ## 🔒 Responsible AI & Data Notes (Mandatory)
# - **Accuracy Disclaimer**: Verify dates, opening hours, travel advisories, and prices before booking or departing.
# - **Safety First**: Follow local guidance and official travel warnings.
# - **Bias Mitigation**: Recommendations aim to be diverse.
# - **Privacy**: No personal identifying information stored.
# - **Agent Status**: Location planning: complete, Activity planning: N/A
# ASSISTANT: # 🎉 Your Custom Trip to Matara
#
# ## Quick Links
# - Dates & Season
# - Recommended Destinations
# - Packing Essentials
# - Responsible AI Notes
#
# ---
#
# ## Hello there! Your exciting trip to **Matara** is all set. Here's a creative overview of your personalized itinerary:
#
# ## 🗓️ Dates & Season
# - **Dates**: October 20, 2025, to October 25, 2025
# - **Duration**: October 20, 2025, to October 25, 2025
# - **Season**: Northeast Monsoon in Sri Lanka, great for North/East coast exploration
#
# ## 👥 Who's Traveling?
# - **Travelers**: 4 people
# - **Type**: Family trip
#
# ## 🎯 Your Vibe
# - **Interests**: Beach, Mountains
#
# ## 🗺️ Recommended Destinations
# 1. **Polhena Beach** (Beach)
#    - Ideal for families in late October
#    - Calm, shallow waters for safe swimming and snorkeling
#    - Warm and sunny weather (26-30°C)
#
# 2. **Mirissa Beach & Whale Watching** (Adventure/Nature/Beach)
#    - Whale and dolphin watching season starts in late October
#    - Relaxing beach with sunny periods and potential brief showers
#
# 3. **Dondra Head Lighthouse** (Scenic)
#    - Breathtaking views of the Indian Ocean
#    - Pleasant, warm weather for exploration
#
# 4. **Weherahena Raja Maha Viharaya (Weherahena Temple)** (Cultural/Scenic)
#    - Significant Buddhist temple with cultural richness
#    - Enjoyable visit regardless of weather
#
# ## 🎡 Daily Activities
# ### 📅 2026-07-16
# - **Morning**: Visit Sigiriya Rock
#
# ## 🎒 Suggested Packing List
# ### Essentials
# - Sunscreen (High UV index in Sri Lanka)
#
# ---
#
# ## 🔒 Responsible AI & Data Notes (Mandatory)
# - **Accuracy Disclaimer**: Verify dates, opening hours, travel advisories, and prices before booking or departing.
# - **Safety First**: Follow local guidance and official travel warnings.
# - **Bias Mitigation**: Recommendations aim to be diverse.
# - **Privacy**: No personal identifying information stored.
# - **Agent Status**: Location planning: complete, Activity planning: N/A
#
#
# --- DEMO 2: Provide Answer 1 (Destination) ---
# --- ROUTER: Classifying user intent for: We want to go to Galle....
# E0000 00:00:1759342086.770986   22572 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
# DEBUG: Raw Model Response: content='' additional_kwargs={'function_call': {'name': 'AgentRouteDecision', 'arguments': '{"next_agent": "location_agent"}'}} response_metadata={'promp
# t_feedback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.5-flash', 'safety_ratings': []} id='run--3b2ca367-f5e0-471e-9368-2baf97733b
# 86-0' tool_calls=[{'name': 'AgentRouteDecision', 'args': {'next_agent': 'location_agent'}, 'id': '85713c02-5b5b-4c8e-87fe-2b05837c879d', 'type': 'tool_call'}] usage_metadata={'input_tokens': 367, 'output_tokens': 60, 'total_tokens': 427, 'input_token_details': {'cache_read': 0}, 'output_token_details': {'reasoning': 41}}
# Next agent name: location_agent
# --- NODE: Location Agent Executing...
# [Comm Flow] User → LocationAgent → Gemini
# DEBUG: [LocationAgent] Parsed response: {'recommended_locations': [{'name': 'Mirissa Beach', 'type': 'Beach, Adventure', 'reason': 'Mirissa is famous for its crescent-shaped beach
# and is a prime spot for whale watching. October marks the beginning of the prime whale watching season, offering an exciting family adventure to spot magnificent whales and dolphin
# s. The weather during this inter-monsoon period is typically warm and sunny with occasional refreshing showers, perfect for enjoying the golden sands, swimming, and experiencing th
# e lively beach atmosphere.'}, {'name': 'Polhena Beach', 'type': 'Beach, Nature', 'reason': 'Known for its natural coral reef, Polhena creates a sheltered lagoon with calm and shall
# ow waters, making it ideal for safe family swimming and snorkeling, especially for children. October, being the inter-monsoon period, features warm, often sunny weather with interm
# ittent light rain, ensuring pleasant conditions for enjoying the beach and exploring its diverse marine life close to the shore.'}, {'name': 'Handunugoda Tea Estate (Herman Teas)',
#  'type': 'Cultural, Scenic, Nature', 'reason': "Located amidst rolling hills and lush greenery inland from Matara, this tea estate offers a scenic escape and a cultural experience
# into Sri Lanka's tea production, satisfying the 'mountains' preference with its elevated landscapes. In October, the weather is typically pleasant with a mix of sunshine and occasi
# onal light rain, keeping the tea fields vibrant and offering a refreshing climate for a guided tour and tea tasting."}, {'name': 'Dondra Head Lighthouse', 'type': 'Scenic, Cultural
# ', 'reason': 'As the southernmost tip of Sri Lanka, Dondra Head offers breathtaking panoramic views of the Indian Ocean from its historic lighthouse, providing a scenic experience
# for the whole family. October typically presents clear visibility, allowing for stunning photographs of the coastline, and the constant sea breeze offers a refreshing break from the warm inter-monsoon temperatures, making it a memorable visit.'}], 'status': 'complete', 'disclaimer': 'Recommendations are generated fairly and do not store personal user data.'}
# ASSISTANT: Here are some location ideas based on your query:
#
# {
#   "recommended_locations": [
#     {
#       "name": "Mirissa Beach",
#       "type": "Beach, Adventure",
#       "reason": "Mirissa is famous for its crescent-shaped beach and is a prime spot for whale watching. October marks the beginning of the prime whale watching season, offering an
#  exciting family adventure to spot magnificent whales and dolphins. The weather during this inter-monsoon period is typically warm and sunny with occasional refreshing showers, perfect for enjoying the golden sands, swimming, and experiencing the lively beach atmosphere."
#     },
#     {
#       "name": "Polhena Beach",
#       "type": "Beach, Nature",
#       "reason": "Known for its natural coral reef, Polhena creates a sheltered lagoon with calm and shallow waters, making it ideal for safe family swimming and snorkeling, especia
# lly for children. October, being the inter-monsoon period, features warm, often sunny weather with intermittent light rain, ensuring pleasant conditions for enjoying the beach and exploring its diverse marine life close to the shore."
#     },
#     {
#       "name": "Handunugoda Tea Estate (Herman Teas)",
#       "type": "Cultural, Scenic, Nature",
#       "reason": "Located amidst rolling hills and lush greenery inland from Matara, this tea estate offers a scenic escape and a cultural experience into Sri Lanka's tea production
# , satisfying the 'mountains' preference with its elevated landscapes. In October, the weather is typically pleasant with a mix of sunshine and occasional light rain, keeping the tea fields vibrant and offering a refreshing climate for a guided tour and tea tasting."
#     },
#     {
#       "name": "Dondra Head Lighthouse",
#       "type": "Scenic, Cultural",
#       "reason": "As the southernmost tip of Sri Lanka, Dondra Head offers breathtaking panoramic views of the Indian Ocean from its historic lighthouse, providing a scenic experien
# ce for the whole family. October typically presents clear visibility, allowing for stunning photographs of the coastline, and the constant sea breeze offers a refreshing break from the warm inter-monsoon temperatures, making it a memorable visit."
#     }
#   ],
#   "status": "complete",
#   "disclaimer": "Recommendations are generated fairly and do not store personal user data."
# }
#
#
# --- DEMO 3: Provide Answer 2 (Dates) ---
# --- ROUTER: Classifying user intent for: We'll go from 2026-07-15 to 2026-07-28....
# E0000 00:00:1759342113.317972   22572 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
# DEBUG: Raw Model Response: content='' additional_kwargs={'function_call': {'name': 'AgentRouteDecision', 'arguments': '{"next_agent": "orchestrator_agent"}'}} response_metadata={'prompt_feedback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.5-flash', 'safety_ratings': []} id='run--8b187565-937f-49b3-a560-3216453b774a-0' tool_calls=[{'name': 'AgentRouteDecision', 'args': {'next_agent': 'orchestrator_agent'}, 'id': '077370d6-d973-47be-bb58-9f01c7676435', 'type': 'tool_call'}] usage_metadata={'input_tokens': 389, 'output_tokens': 63, 'total_tokens': 452, 'input_token_details': {'cache_read': 0}, 'output_token_details': {'reasoning': 42}}
# Next agent name: orchestrator_agent
# --- NODE: Orchestrator Agent Executing...
#
# Debug: Original input length: 39 characters, 6 words
#
#
# > Entering new AgentExecutor chain...
#
# Invoking: `extract_dates` with `{'start_date': '2026-07-15', 'end_date': '2026-07-28', 'current_date': '2025-10-01'}`
#
#
# extract_dates is not a valid tool, try one of [].
# Invoking: `extract_season` with `{'start_date': '2026-07-15'}`
#
#
# extract_season is not a valid tool, try one of [].{
#   "destination": null,
#   "start_date": null,
#   "end_date": null,
#   "no_of_traveler": null,
#   "season": null,
#   "budget": null,
#   "user_preferences": [],
#   "type_of_trip": null
# }
#
# > Finished chain.
# DEBUG: Orchestrator Agent RAW LLM Extraction: destination=None season=None start_date=None end_date=None user_preferences=[] no_of_traveler=None budget=None type_of_trip=None additional_info=None status=None messages=[]
# DEBUG missing fields: ['destination', 'start_date', 'end_date', 'no_of_traveler', 'type_of_trip', 'user_preferences']
#
# What specific destination in Sri Lanka are you interested in visiting for your trip? ➡️ paris
# DEBUG missing fields: ['start_date', 'end_date', 'no_of_traveler', 'type_of_trip', 'user_preferences']
#
# When do you plan to start your trip to Paris? ➡️ 2025-10-12
# DEBUG: Auto-updated season to Northeast Monsoon after date input.
# DEBUG missing fields: ['end_date', 'no_of_traveler', 'type_of_trip', 'user_preferences']
#
# When do you plan to return from your trip to Paris? ➡️ 2025-10-15
# DEBUG missing fields: ['no_of_traveler', 'type_of_trip', 'user_preferences']
#
# How many travelers will be joining you on your trip to Sri Lanka? ➡️ 4
# DEBUG missing fields: ['type_of_trip', 'user_preferences']
#
# What type of trip are you planning for your visit to Paris? (e.g. leisure, business, adventure, cultural) ➡️ leisure
# DEBUG missing fields: ['user_preferences']
#
# What are your preferences or interests when traveling to Sri Lanka? This will help me tailor the trip recommendations to suit your tastes and make your experience more enjoyable! ➡️ have fun and adventure
# DEBUG missing fields: []
# --- NODE: Location Agent Executing...
# [Comm Flow] User → LocationAgent → Gemini
# DEBUG: [LocationAgent] Parsed response: {'recommended_locations': [{'name': 'Disneyland Paris', 'type': 'Adventure/Entertainment', 'reason': "Mid-October is an ideal time for 'fun
# and adventure' at Disneyland Paris, as the parks are typically adorned for Halloween. This seasonal decoration adds a unique festive atmosphere with special parades and attractions
# , perfectly aligning with your preferences. While the weather in mid-October can be cool and crisp (average temperatures 8-15°C/46-59°F), many attractions are indoors, and the fest
# ive spirit makes it enjoyable, with potentially fewer crowds than peak summer."}, {'name': 'The Paris Catacombs', 'type': 'Adventure/Cultural', 'reason': "For a truly unique and ad
# venturous experience, the Paris Catacombs offer an intriguing journey through underground ossuaries. Visiting in mid-October, when the weather can be cool and occasionally overcast
#  (average temperatures 8-15°C/46-59°F), enhances the mysterious and atmospheric ambiance. It's an indoor activity, making it suitable regardless of autumn showers, and offers a com
# pelling dive into a hidden part of Parisian history."}, {'name': 'Montmartre and Sacré-Cœur Basilica', 'type': 'Cultural/Scenic/Exploration', 'reason': "Exploring the charming, win
# ding streets of Montmartre provides a delightful blend of 'fun and adventure' with its artistic ambiance and stunning city views from the Sacré-Cœur. In mid-October, the autumn lig
# ht is beautiful, and the weather is typically crisp (average temperatures 8-15°C/46-59°F), perfect for a leisurely stroll, enjoying street artists, and discovering cozy cafes. It's
#  a fantastic way to experience a bohemian side of Paris at a pleasant time of year."}, {'name': 'Seine River Cruise (e.g., Bateaux Mouches)', 'type': 'Scenic/Leisure', 'reason': "A
#  leisurely Seine River cruise is an excellent way to see Paris's iconic landmarks from a unique perspective, suitable for all four travelers. In mid-October, you can enjoy the beau
# tiful autumn scenery along the riverbanks as leaves begin to change. While it might be cool (average temperatures 8-15°C/46-59°F), most boats offer enclosed seating with heating, m
# aking it a comfortable and scenic activity regardless of the weather. Evening cruises are particularly magical with the city lights."}], 'status': 'complete', 'disclaimer': 'Recommendations are generated fairly and do not store personal user data.'}
# Executing Activity Agent: Generating activity plans...
# Executing Packing Agent: Generating packing list...
# --- NODE: Summary Agent Executing...
#
# DEBUG: Generating summary for state: {'destination': 'paris', 'season': 'Northeast Monsoon', 'start_date': '2025-10-12', 'end_date': '2025-10-15', 'user_preferences': ['have fun an
# d adventure'], 'no_of_traveler': 4, 'budget': None, 'type_of_trip': 'leisure', 'additional_info': None, 'status': 'completed', 'messages': [], 'location_recommendations': {'recomme
# nded_locations': [{'name': 'Disneyland Paris', 'type': 'Adventure/Entertainment', 'reason': "Mid-October is an ideal time for 'fun and adventure' at Disneyland Paris, as the parks
# are typically adorned for Halloween. This seasonal decoration adds a unique festive atmosphere with special parades and attractions, perfectly aligning with your preferences. While
#  the weather in mid-October can be cool and crisp (average temperatures 8-15°C/46-59°F), many attractions are indoors, and the festive spirit makes it enjoyable, with potentially f
# ewer crowds than peak summer."}, {'name': 'The Paris Catacombs', 'type': 'Adventure/Cultural', 'reason': "For a truly unique and adventurous experience, the Paris Catacombs offer a
# n intriguing journey through underground ossuaries. Visiting in mid-October, when the weather can be cool and occasionally overcast (average temperatures 8-15°C/46-59°F), enhances
# the mysterious and atmospheric ambiance. It's an indoor activity, making it suitable regardless of autumn showers, and offers a compelling dive into a hidden part of Parisian histo
# ry."}, {'name': 'Montmartre and Sacré-Cœur Basilica', 'type': 'Cultural/Scenic/Exploration', 'reason': "Exploring the charming, winding streets of Montmartre provides a delightful
# blend of 'fun and adventure' with its artistic ambiance and stunning city views from the Sacré-Cœur. In mid-October, the autumn light is beautiful, and the weather is typically cri
# sp (average temperatures 8-15°C/46-59°F), perfect for a leisurely stroll, enjoying street artists, and discovering cozy cafes. It's a fantastic way to experience a bohemian side of
#  Paris at a pleasant time of year."}, {'name': 'Seine River Cruise (e.g., Bateaux Mouches)', 'type': 'Scenic/Leisure', 'reason': "A leisurely Seine River cruise is an excellent way
#  to see Paris's iconic landmarks from a unique perspective, suitable for all four travelers. In mid-October, you can enjoy the beautiful autumn scenery along the riverbanks as leav
# es begin to change. While it might be cool (average temperatures 8-15°C/46-59°F), most boats offer enclosed seating with heating, making it a comfortable and scenic activity regard
# less of the weather. Evening cruises are particularly magical with the city lights."}], 'status': 'complete', 'disclaimer': 'Recommendations are generated fairly and do not store p
# ersonal user data.'}, 'activity_recommendations': {'day_plans': [{'date': '2026-07-16', 'suggestions': [{'title': 'Visit Sigiriya Rock', 'time_of_day': 'morning'}]}]}, 'packing_list': {'categories': [{'name': 'Essentials', 'items': [{'name': 'Sunscreen', 'reason': 'High UV index in Sri Lanka'}]}]}}
#
# DEBUG: Final polished summary: # Trip Summary: Your Custom Trip to Paris
#
# ## Quick Links
# - Dates & Season
# - Recommended Destinations
# - Packing Essentials
# - Responsible AI Notes
#
# ---
#
# ## Overview
# Welcome to your personalized trip to **Paris**! Below is a detailed summary of your itinerary.
#
# ## 🗓️ Dates & Season
# - **Dates**: October 12, 2025, to October 15, 2025
# - **Duration**: 4 days
# - **Season**: Northeast Monsoon in Sri Lanka
#
# ## 👥 Travelers
# - **Number of Travelers**: 4
# - **Trip Type**: Leisure
#
# ## 🎯 Your Interests
# - **Interests**: Fun and adventure
#
# ## 🗺️ Recommended Destinations
# 1. **Disneyland Paris** (Adventure/Entertainment)
#    - Ideal for fun and adventure with Halloween decorations and special events.
#    - Weather: Cool and crisp, suitable for indoor activities.
#
# 2. **The Paris Catacombs** (Adventure/Cultural)
#    - Unique underground ossuaries experience.
#    - Weather: Cool and occasionally overcast, indoor activity.
#
# 3. **Montmartre and Sacré-Cœur Basilica** (Cultural/Scenic/Exploration)
#    - Charming streets, artistic ambiance, and stunning views.
#    - Weather: Crisp autumn days, perfect for strolling.
#
# 4. **Seine River Cruise** (Scenic/Leisure)
#    - Enjoy iconic landmarks from a unique perspective.
#    - Weather: Cool, boats offer enclosed seating.
#
# ## 🎡 Daily Activities
# - **2026-07-16**
#    - **Morning**: Visit Sigiriya Rock
#
# ## 🎒 Suggested Packing List
# ### Essentials
# - Sunscreen: High UV index in Sri Lanka
#
# ---
#
# ## 🔒 Responsible AI & Data Notes
# - **Accuracy Disclaimer**: Verify dates, opening hours, and prices before booking.
# - **Safety First**: Follow local guidance and travel warnings.
# - **Bias Mitigation**: Recommendations aim to be diverse.
# - **Privacy**: No personal identifying information is stored.
# - **Agent Status**: Location planning: complete, Activity planning: N/A
# ASSISTANT: # Trip Summary: Your Custom Trip to Paris
#
# ## Quick Links
# - Dates & Season
# - Recommended Destinations
# - Packing Essentials
# - Responsible AI Notes
#
# ---
#
# ## Overview
# Welcome to your personalized trip to **Paris**! Below is a detailed summary of your itinerary.
#
# ## 🗓️ Dates & Season
# - **Dates**: October 12, 2025, to October 15, 2025
# - **Duration**: 4 days
# - **Season**: Northeast Monsoon in Sri Lanka
#
# ## 👥 Travelers
# - **Number of Travelers**: 4
# - **Trip Type**: Leisure
#
# ## 🎯 Your Interests
# - **Interests**: Fun and adventure
#
# ## 🗺️ Recommended Destinations
# 1. **Disneyland Paris** (Adventure/Entertainment)
#    - Ideal for fun and adventure with Halloween decorations and special events.
#    - Weather: Cool and crisp, suitable for indoor activities.
#
# 2. **The Paris Catacombs** (Adventure/Cultural)
#    - Unique underground ossuaries experience.
#    - Weather: Cool and occasionally overcast, indoor activity.
#
# 3. **Montmartre and Sacré-Cœur Basilica** (Cultural/Scenic/Exploration)
#    - Charming streets, artistic ambiance, and stunning views.
#    - Weather: Crisp autumn days, perfect for strolling.
#
# 4. **Seine River Cruise** (Scenic/Leisure)
#    - Enjoy iconic landmarks from a unique perspective.
#    - Weather: Cool, boats offer enclosed seating.
#
# ## 🎡 Daily Activities
# - **2026-07-16**
#    - **Morning**: Visit Sigiriya Rock
#
# ## 🎒 Suggested Packing List
# ### Essentials
# - Sunscreen: High UV index in Sri Lanka
#
# ---
#
# ## 🔒 Responsible AI & Data Notes
# - **Accuracy Disclaimer**: Verify dates, opening hours, and prices before booking.
# - **Safety First**: Follow local guidance and travel warnings.
# - **Bias Mitigation**: Recommendations aim to be diverse.
# - **Privacy**: No personal identifying information is stored.
# - **Agent Status**: Location planning: complete, Activity planning: N/A
#
#
# --- DEMO 4: Complete Data & Generate Plan ---
# --- ROUTER: Classifying user intent for: This is a leisure trip with a medium budget....
# E0000 00:00:1759342542.903568   22572 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
# DEBUG: Raw Model Response: content='' additional_kwargs={'function_call': {'name': 'AgentRouteDecision', 'arguments': '{"next_agent": "chat_agent"}'}} response_metadata={'prompt_fe
# edback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.5-flash', 'safety_ratings': []} id='run--6bd29e80-8c7b-4195-9193-b46da8e1f5fd-0
# ' tool_calls=[{'name': 'AgentRouteDecision', 'args': {'next_agent': 'chat_agent'}, 'id': 'cf87e2d5-eac8-4b77-81c2-f01a23509c22', 'type': 'tool_call'}] usage_metadata={'input_tokens': 370, 'output_tokens': 96, 'total_tokens': 466, 'input_token_details': {'cache_read': 0}, 'output_token_details': {'reasoning': 77}}
# Next agent name: chat_agent
# --- NODE: Chat Agent Executing...
# DEBUG: Chat Agent Raw Model Response: content='Got it! Here are some suggestions for your leisure trip to Matara with a medium budget:\n\n1. **Accommodation**: Consider staying at
# guesthouses or mid-range hotels in Matara. Look for options that offer a balance between comfort and affordability.\n\n2. **Transportation**: Opt for public transportation like bus
# es or trains to explore Matara and its surrounding areas. You can also consider renting a car for more flexibility.\n\n3. **Food**: Enjoy delicious local cuisine at affordable eate
# ries and street food stalls to experience the authentic flavors of Sri Lanka without breaking the bank.\n\n4. **Activities**: Explore the beaches, visit cultural sites like temples
#  and lighthouses, and take part in nature excursions like whale watching at budget-friendly rates.\n\n5. **Shopping**: Shop for souvenirs and local handicrafts at markets and stall
# s to bring back unique mementos from your trip.\n\nBy balancing your expenses and choosing cost-effective options, you can have a memorable leisure trip to Matara within a medium b
# udget. Enjoy your travels!' additional_kwargs={'refusal': None} response_metadata={'token_usage': {'completion_tokens': 208, 'prompt_tokens': 2211, 'total_tokens': 2419, 'completio
# n_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cache
# d_tokens': 0}}, 'model_name': 'gpt-3.5-turbo-0125', 'system_fingerprint': None, 'id': 'chatcmpl-CLveU6I2HSyJLBJbm3dFEfhdl6oDn', 'service_tier': 'default', 'finish_reason': 'stop',
# 'logprobs': None} id='run--eb4ad2bb-e84f-4951-b0aa-44edf0b7727d-0' usage_metadata={'input_tokens': 2211, 'output_tokens': 208, 'total_tokens': 2419, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}
# ASSISTANT:
# Got it! Here are some suggestions for your leisure trip to Matara with a medium budget:
#
# 1. **Accommodation**: Consider staying at guesthouses or mid-range hotels in Matara. Look for options that offer a balance between comfort and affordability.
#
# 2. **Transportation**: Opt for public transportation like buses or trains to explore Matara and its surrounding areas. You can also consider renting a car for more flexibility.
#
# 3. **Food**: Enjoy delicious local cuisine at affordable eateries and street food stalls to experience the authentic flavors of Sri Lanka without breaking the bank.
#
# 4. **Activities**: Explore the beaches, visit cultural sites like temples and lighthouses, and take part in nature excursions like whale watching at budget-friendly rates.
#
# 5. **Shopping**: Shop for souvenirs and local handicrafts at markets and stalls to bring back unique mementos from your trip.
#
# By balancing your expenses and choosing cost-effective options, you can have a memorable leisure trip to Matara within a medium budget. Enjoy your travels!
#
#
# --- DEMO 5: Refine Summary (Refiner Agent) ---
# --- ROUTER: Classifying user intent for: Make the summary shorter and add emojis to the sec...
# E0000 00:00:1759342546.362071   22572 alts_credentials.cc:93] ALTS creds ignored. Not running on GCP and untrusted ALTS is not enabled.
# DEBUG: Raw Model Response: content='' additional_kwargs={'function_call': {'name': 'AgentRouteDecision', 'arguments': '{"next_agent": "chat_agent"}'}} response_metadata={'prompt_fe
# edback': {'block_reason': 0, 'safety_ratings': []}, 'finish_reason': 'STOP', 'model_name': 'gemini-2.5-flash', 'safety_ratings': []} id='run--b977ad1d-6464-4506-95a1-04b0fcafc564-0
# ' tool_calls=[{'name': 'AgentRouteDecision', 'args': {'next_agent': 'chat_agent'}, 'id': '1c989f17-3a90-4dce-b959-e739797a7095', 'type': 'tool_call'}] usage_metadata={'input_tokens': 372, 'output_tokens': 181, 'total_tokens': 553, 'input_token_details': {'cache_read': 0}, 'output_token_details': {'reasoning': 162}}
# Next agent name: chat_agent
# --- NODE: Summary Refiner Executing...
# ASSISTANT:
# # Trip Summary: Your Paris Adventure 🇫🇷
#
# ## Quick Links 📌
# - Dates & Season 🗓️
# - Recommended Destinations 🗺️
# - Packing Essentials 🎒
# - Responsible AI Notes 🔒
#
# ---
#
# ## Overview
# Welcome to your personalized trip to **Paris**! Here's a brief overview of your adventure.
#
# ## 🗓️ Dates & Season
# - **Dates**: October 12-15, 2025
# - **Duration**: 4 days
# - **Season**: Northeast Monsoon in Sri Lanka
#
# ## 👥 Travelers
# - **Travelers**: 4
# - **Type**: Leisure
#
# ## 🎯 Your Interests
# - **Interests**: Fun and adventure
#
# ## 🗺️ Recommended Destinations
# 1. **Disneyland Paris** 🎢
#    - Ideal for fun and adventure with Halloween vibes.
#    - Weather: Cool and crisp, perfect for indoor activities.
#
# 2. **The Paris Catacombs** 💀
#    - Unique underground ossuaries experience.
#    - Weather: Cool and occasionally overcast, great for indoor exploration.
#
# 3. **Montmartre and Sacré-Cœur Basilica** 🎨
#    - Charming streets, artistic ambiance, stunning views.
#    - Weather: Crisp autumn days, ideal for leisurely strolls.
#
# 4. **Seine River Cruise** ⛴️
#    - Enjoy iconic landmarks from a unique perspective.
#    - Weather: Cool, boats offer enclosed seating.
#
# ## 🎡 Daily Activities
# - **2026-07-16**
#    - **Morning**: Visit Sigiriya Rock
#
# ## 🎒 Suggested Packing List
# ### Essentials
# - Sunscreen: High UV index in Sri Lanka
#
# ---
#
# ## 🔒 Responsible AI & Data Notes
# - **Accuracy Disclaimer**: Verify dates, opening hours, and prices before booking.
# - **Safety First**: Follow local guidance and travel warnings.
# - **Bias Mitigation**: Recommendations aim to be diverse.
# - **Privacy**: No personal identifying information is stored.
# - **Agent Status**: Location planning: complete, Activity planning: N/A
# (.venv) PS C:\Users\dulha\GitHub\Seasonal_Travel_Recommender>