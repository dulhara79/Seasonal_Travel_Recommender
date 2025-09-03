# orchestrator_agent.py
from typing import Optional
from schemas import UserMessage, Slots, FinalResponse, AgentTrace, LocationOut, ActivitiesOut, PackingOut
from utils import normalize_dates, extract_entities, join_nonempty
from vector_memory import VectorMemory
from llm import chat_completion

# Import your group members' agents
from agents.location_agent import LocationAgent
from agents.activity_agent import ActivityAgent
from agents.packinglist_agent import PackingListAgent

class ConversationMemory:
    def __init__(self):
        self.messages = []

    def add(self, role, text):
        self.messages.append({"role": role, "content": text})

    def get_messages(self):
        return self.messages[-20:]

class OrchestratorAgent:
    def __init__(self):
        self.vector_memory = VectorMemory()
        self.memory = ConversationMemory()
        # initialize the other agents
        self.location_agent = LocationAgent(self.vector_memory)
        self.activity_agent = ActivityAgent(self.vector_memory)
        self.packing_agent = PackingListAgent(self.vector_memory)

    def handle_message(self, msg: UserMessage) -> FinalResponse:
        text = msg.text
        # --- Step 1: Extract entities and dates ---
        entities = extract_entities(text)
        start_date, end_date = normalize_dates(text)

        # --- Step 2: Retrieve past context ---
        previous = self.vector_memory.query(text, top_k=3)
        retrieved_notes = "\n".join([p.get("text","") for p in previous])

        # --- Step 3: Compose system prompt for LLM ---
        system_prompt = (
            "You are a travel assistant. User wants travel recommendations. "
            "Use previous context and current input to extract destination, dates, preferences, activities, etc. "
            "If insufficient info, ask clarifying questions."
        )
        messages = [{"role": "system", "content": system_prompt}]
        if retrieved_notes:
            messages.append({"role": "system", "content": f"Previous notes:\n{retrieved_notes}"})
        messages.append({"role": "user", "content": text})

        # --- Step 4: Call LLM ---
        llm_response = chat_completion(messages)

        # --- Step 5: Update short-term memory & vector DB ---
        self.memory.add("user", text)
        self.memory.add("assistant", llm_response)
        self.vector_memory.add_document({"text": text, "llm_response": llm_response})

        # --- Step 6: Fill slots ---
        slots = Slots(
            destination=join_nonempty(entities),
            start_date=start_date,
            end_date=end_date,
            preferences=None
        )

        # --- Step 7: Delegation to relevant agents ---
        location_result = None
        activity_result = None
        packing_result = None
        clarifying_question = None

        # Check if destination & dates exist; else ask LLM to clarify
        if not slots.destination or not slots.start_date or not slots.end_date:
            clarifying_question = "Can you tell me your destination and travel dates?"
        else:
            # Call location agent
            location_result = self.location_agent.handle(vars(slots), text)
            # Call activity agent
            activity_result = self.activity_agent.handle(vars(slots), text)
            # Call packing list agent
            packing_result = self.packing_agent.handle(vars(slots), text)

        # --- Step 8: Build structured trace ---
        trace = AgentTrace(
            nlp_json=slots,
            weather_json=location_result,
            activities_json=activity_result,
            packing_json=packing_result,
            clarifying_question=clarifying_question,
            notes=llm_response
        )

        # --- Step 9: Combine final text ---
        responses = []
        if clarifying_question:
            responses.append(clarifying_question)
        if location_result:
            responses.append(location_result)
        if activity_result:
            responses.append(activity_result)
        if packing_result:
            responses.append(packing_result)
        if not responses:
            responses.append(llm_response)

        final_text = "\n\n".join(responses)

        return FinalResponse(text=final_text, trace=trace)
