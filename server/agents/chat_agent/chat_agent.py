import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from server.utils.config import OPENAI_API_KEY, OPENAI_MODEL

# Current Date for temporal grounding
CURRENT_DATE = "October 1, 2025"

# --- 1. The Core System Prompt ---
# This prompt is critical for enforcing all constraints.
SRI_LANKA_CHAT_SYSTEM_PROMPT = f"""
You are the **Chat Agent** for a Sri Lanka travel planning system.
Your role is to engage in friendly, respectful, and helpful conversation with the user while following these rules and guidelines.
Stick to the constraints below strictly.
---

### 🔒 Core Restrictions
1. **Location Restriction:**
   - Absolutely **DO NOT** suggest or discuss travel outside of **Sri Lanka**.
   - If a user asks about other countries, politely remind them that this system is only for Sri Lanka travel.

2. **Date Restriction:**
   - The current date is **{CURRENT_DATE}**.
   - Do not suggest trips or events that are in the past.
   - Only suggest **upcoming, relevant** trips or holidays.

3. **Holiday & Cultural Accuracy:**
   - Use the list of **upcoming Sri Lankan public holidays (2025)** for context and trip ideas:
     - Oct 6 (Vap Poya), Oct 20 (Deepavali), Nov 5 (Ill Poya), Dec 4 (Unduvap Poya), Dec 25 (Christmas).
   - **Important:** When recommending locations for a specific festival, prefer regions where that festival is commonly celebrated by the local community.
     - Example: **Deepavali** is primarily a Hindu/Tamil festival — recommend areas with significant Tamil/Hindu presence (e.g., **Jaffna, Trincomalee, Batticaloa, parts of Colombo**). **Do not** recommend places that are unlikely to host public Deepavali festivities unless you state uncertainty.
   - If you are **not** confident about a local festival schedule or event, explicitly say "I might be mistaken — please verify with local temple/community sources."

---

### 🧭 Travel Suggestion Guidelines
4. **Destination Focus:**
   - Prioritize well-known, safe, and tourist-friendly Sri Lankan destinations (cultural, nature, wildlife, beaches).
   - Include relevant hidden gems when appropriate.

5. **Responsible AI Use:**
   - Provide safe, accurate, and culturally respectful information.
   - Avoid inventing events, schedules, or local ceremonies. If you must, flag them as unverified.

6. **Respect & Tone:**
   - Friendly, warm, respectful; never dismiss user preferences.

7. **Boundaries of Role:**
   - Do not give long rigid multi-day itineraries — route such requests to the Orchestrator via the Decision Agent.

---

### 🌱 Extra Helpful Features
8. **Weather & Season Awareness:**
   - Note Sri Lanka's monsoon seasons and suggest destinations accordingly.

9. **Cultural Respect:**
   - Remind about respectful dress and behavior for religious sites and public ceremonies.

10. **Personalization:**
    - Tailor suggestions when the user gives preferences.

---

### ✅ Example Correct Behavior
- **User:** "Where should I go for Deepavali this year?"
- **Agent:** "Deepavali falls on October 20, 2025. For meaningful Deepavali celebrations in Sri Lanka, consider **Jaffna** or **Trincomalee** (regions with active Hindu temples and community events). You can also check local Hindu temples in **Colombo**. I might be mistaken about specific temple event times — please verify local schedules."

### ❌ Things to Avoid
- Recommending locations outside Sri Lanka.
- Making up event specifics or suggesting places where a festival is not commonly celebrated.
"""

# --- Festival region map & helper utilities ---
FESTIVAL_REGION_MAP = {
    # January
    "duruthu poya": ["colombo", "kelaniya", "anuradhapura", "kandy"],
    "thai pongal": ["jaffna", "batticaloa", "trincomalee", "colombo"],
    "nallur festival": ["jaffna"],

    # February
    "navam perahera": ["colombo", "kelaniya"],
    "maha shivaratri": ["trincomalee", "jaffna", "kataragama", "colombo"],
    "national day": ["colombo", "kandy", "galle", "anuradhapura"],

    # March
    "madin poya": ["anuradhapura", "polonnaruwa", "kandy", "colombo"],
    "mawlid": ["colombo", "kandy", "jaffna", "galle"],
    "holi": ["jaffna", "batticaloa", "colombo"],

    # April
    "sinhala and tamil new year": ["colombo", "jaffna", "galle", "kandy", "negombo"],
    "bak poya": ["anuradhapura", "kandy", "colombo"],
    "good friday": ["colombo", "negombo", "galle", "kandy"],
    "easter": ["colombo", "negombo", "galle", "kandy"],

    # May
    "vesak": ["colombo", "kandy", "anuradhapura", "polonnaruwa", "kelaniya"],
    "labour day": ["colombo", "kandy", "galle"],

    # June
    "poson poya": ["anuradhapura", "mihintale", "kandy", "colombo"],  # Note: mihintale not in ALL_DESTINATIONS, but key site
    "eid al-adha": ["colombo", "kandy", "jaffna", "galle"],

    # July
    "esala perahera": ["kandy", "colombo", "ratnapura"],
    "kataragama festival": ["kataragama", "yala national park", "tissamaharama"],
    "vel festival": ["colombo"],

    # August
    "nikini poya": ["anuradhapura", "kandy"],
    "nallur kandaswamy festival": ["jaffna"],
    "milad un nabi": ["colombo", "kandy", "jaffna", "galle"],
    "raksha bandhan": ["jaffna", "batticaloa", "colombo"],
    "ganesh chaturthi": ["jaffna", "colombo"],

    # September
    "binara poya": ["anuradhapura", "kandy"],

    # October
    "vap poya": ["kandy", "anuradhapura", "polonnaruwa", "kelaniya", "colombo"],
    "dussehra": ["jaffna", "batticaloa", "colombo"],
    "deepavali": ["jaffna", "trincomalee", "batticaloa", "colombo"],

    # November
    "ill poya": ["anuradhapura", "polonnaruwa", "kandy"],

    # December
    "unduvap poya": ["anuradhapura", "kandy"],
    "christmas": ["colombo", "negombo", "nuwara eliya", "galle"]
}

# canonical list of Sri Lanka destinations we recommend (lowercased for matching)
# Added "mihintale" as it's a key site for Poson, but if strict, can remove or map to anuradhapura
ALL_DESTINATIONS = [
    "sigiriya","anuradhapura","polonnaruwa","kandy","ella","nuwara eliya","horton plains",
    "knuckles range","yala national park","wilpattu","minneriya","mirissa","arugam bay",
    "trincomalee","galle","unawatuna","bentota","jaffna","batticaloa","colombo","negombo",
    "dambulla","hikkaduwa","kataragama","tissamaharama","pasikudah","matara","ratnapura",
    "adam's peak","haputale","tangalle", "mihintale"
]

def detect_festival(text: str):
    t = text.lower()
    for k in FESTIVAL_REGION_MAP.keys():
        if k in t:
            return k
    return None

def extract_locations_from_text(text: str):
    t = text.lower()
    found = []
    for loc in ALL_DESTINATIONS:
        if loc in t:
            found.append(loc)
    return found

def sanitize_festival_recommendations(response_text: str, user_query: str) -> str:
    """
    If the user query mentions a festival, ensure the model's suggestions include at least
    one culturally-relevant location from FESTIVAL_REGION_MAP. If not, append a corrective sentence
    with appropriate suggestions (and note a verification recommendation).
    """
    festival = detect_festival(user_query) or detect_festival(response_text)
    if not festival:
        # Also ensure no foreign location accidentally suggested:
        # If any known non-SL location appears, remove it (simple heuristic).
        if "bali" in response_text.lower() or "thailand" in response_text.lower():
            return response_text + "\n\nNote: I can only recommend destinations inside Sri Lanka — would you like Sri Lanka alternatives?"
        return response_text

    suggested = extract_locations_from_text(response_text)
    allowed = FESTIVAL_REGION_MAP.get(festival, [])
    # if any suggested intersects allowed -> OK
    if any(loc in allowed for loc in suggested):
        return response_text
    # otherwise append corrective guidance
    allowed_readable = ", ".join([loc.title() for loc in allowed])
    correction = (
        f"\n\nNote: For **{festival.title()}** (the festival you mentioned), "
        f"regions where this festival is commonly celebrated in Sri Lanka include: {allowed_readable}. "
        "I recommend considering those places for culturally meaningful celebrations. "
        "I might be mistaken about exact event schedules — please verify local temple/community event timings."
    )
    return response_text + correction


# --- 2. Create the Chat Agent Runnable ---
def create_chat_agent_chain():
    """
    Creates the LangChain runnable for the Chat Agent using the OpenAI API.
    """
    # Use a conversational model
    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.7)

    # Define the chat prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SRI_LANKA_CHAT_SYSTEM_PROMPT),
            # This is where LangChain manages the conversation history for context
            ("placeholder", "{chat_history}"),
            ("human", "{user_query}")
        ]
    )

    # Create the chain
    chat_chain = prompt | llm

    return chat_chain


# --- 3. Define the LangGraph Node Function ---
# In LangGraph, the Chat Agent node manages the state update.
def chat_agent_node(state: dict) -> dict:
    """
    The function that acts as the LangGraph node for the Chat Agent.
    It handles simple conversations and general queries.
    """
    chat_chain = create_chat_agent_chain()
    user_query = state["user_query"]

    # Simple agents often only need the last query,
    # but a true chat agent needs the full history (state["chat_history"])

    # We'll simulate a simple chat agent for routing here:
    response = chat_chain.invoke({
        "user_query": user_query,
        "chat_history": state.get("chat_history", [])
    })

    print(f"DEBUG: Chat Agent Raw Model Response: {response}")

    friendly_response = response.content

    # --- Sanitize festival/region-sensitive replies ---
    friendly_response = sanitize_festival_recommendations(friendly_response, user_query)

    # Update the conversation history
    state["chat_history"].append(("human", user_query))
    state["chat_history"].append(("ai", friendly_response))

    state["final_summary"] = friendly_response

    return state

# --- Example of How the Agent Responds ---
# chat_func = chat_agent_node
# test_state = {
#     "user_query": "Hey, can you tell more details about the galle fort?",
#     "chat_history": []
# }
#
# new_state = chat_func(test_state)
# print(new_state["final_summary"])
# >>> Expected Output: A friendly response suggesting Jaffna or a similar location, mentioning the Oct 20th date.
#
# (.venv) PS C:\Users\dulha\GitHub\Seasonal_Travel_Recommender> python -m server.agents.chat_agent.chat_agent
# DEBUG: Chat Agent Raw Model Response: content="Of course! Galle Fort is a fascinating UNESCO World Heritage Site located in the coastal city of Galle in southern Sri Lanka. This hi
# storic fort is known for its well-preserved 17th-century Dutch colonial architecture, charming cobblestone streets, and stunning views of the Indian Ocean.\n\nWithin the fort walls
# , you can explore a mix of boutique shops, art galleries, cafes, and museums. Don't miss the iconic Galle Lighthouse, which offers panoramic views of the fort and the surrounding a
# rea. The fort also houses several historic churches, mosques, and the Dutch Reformed Church.\n\nFor a unique experience, you can walk along the fort ramparts at sunset, offering br
# eathtaking views of the ocean and the town. Galle Fort is a perfect blend of history, culture, and scenic beauty, making it a must-visit destination for travelers exploring Sri Lan
# ka." additional_kwargs={'refusal': None} response_metadata={'token_usage': {'completion_tokens': 174, 'prompt_tokens': 741, 'total_tokens': 915, 'completion_tokens_details': {'acce
# pted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_na
# me': 'gpt-3.5-turbo-0125', 'system_fingerprint': None, 'id': 'chatcmpl-CLpjvjwEPZZHTYtENy9pUoqpVmyNv', 'service_tier': 'default', 'finish_reason': 'stop', 'logprobs': None} id='run
# --d2680f16-dede-4f34-af24-7081ff75f247-0' usage_metadata={'input_tokens': 741, 'output_tokens': 174, 'total_tokens': 915, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}
# Of course! Galle Fort is a fascinating UNESCO World Heritage Site located in the coastal city of Galle in southern Sri Lanka. This historic fort is known for its well-preserved 17th-century Dutch colonial architecture, charming cobblestone streets, and stunning views of the Indian Ocean.
#
# Within the fort walls, you can explore a mix of boutique shops, art galleries, cafes, and museums. Don't miss the iconic Galle Lighthouse, which offers panoramic views of the fort and the surrounding area. The fort also houses several historic churches, mosques, and the Dutch Reformed Church.
#
# For a unique experience, you can walk along the fort ramparts at sunset, offering breathtaking views of the ocean and the town. Galle Fort is a perfect blend of history, culture, and scenic beauty, making it a must-visit destination for travelers exploring Sri Lanka.
#