# from dotenv import load_dotenv
# from pydantic import BaseModel
# from langchain_openai import ChatOpenAI
# from langchain_anthropic import ChatAnthropic
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import PydanticOutputParser
# from langchain.agents import create_tool_calling_agent, AgentExecutor
# from tools import search_tool, wiki_tool, save_tool
# import os
# import pathlib

# # Load .env that sits next to this file
# load_dotenv()

# api_key = os.getenv("OPENAI_API_KEY")
# if not api_key:
#     raise RuntimeError("OPENAI_API_KEY not set. Put it in .env or env vars.")
# else:
#     print("OPENAI_API_KEY loaded")
#     print(f"OPENAI_API_KEY: {api_key[:4]}...")


# class ResearchResponse(BaseModel):
#     topic: str
#     summary: str
#     sources: list[str]
#     tools_used: list[str]
    

# # llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=api_key)
# parser = PydanticOutputParser(pydantic_object=ResearchResponse)

# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             """
#             You are a research assistant that will help generate a research paper.
#             Answer the user query and use neccessary tools. 
#             Wrap the output in this format and provide no other text\n{format_instructions}
#             """,
#         ),
#         ("placeholder", "{chat_history}"),
#         ("human", "{query}"),
#         ("placeholder", "{agent_scratchpad}"),
#     ]
# ).partial(format_instructions=parser.get_format_instructions())

# tools = [search_tool, wiki_tool, save_tool]
# agent = create_tool_calling_agent(
#     llm=llm,
#     prompt=prompt,
#     tools=tools
# )

# agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
# query = input("who is the prime minister of srilanka ")
# raw_response = agent_executor.invoke({"query": query})

# try:
#     structured_response = parser.parse(raw_response.get("output")[0]["text"])
#     print(structured_response)
# except Exception as e:
#     print("Error parsing response", e, "Raw Response - ", raw_response)

# travel_agent.py
# ----------------
# A focused "Travel Agent" research assistant powered by LangChain.
# It ONLY answers travel-related queries (destinations, itineraries, costs, visas,
# weather, transport, safety, attractions, etc.). Non-travel questions receive a gentle refusal.

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from datetime import datetime
import os

# ----------------
# 1) Environment
# ----------------
# Load .env that sits next to this file (expects OPENAI_API_KEY)
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not set. Put it in .env or env vars.")
else:
    print("OPENAI_API_KEY loaded")
    print(f"OPENAI_API_KEY: {api_key[:4]}...")

# ----------------
# 2) Pydantic schema (Travel-only output)
# ----------------
class TravelResponse(BaseModel):
    # High-level classification so you can branch on it later if needed
    query_type: str = Field(
        description="One of: itinerary, visa, safety, costs, weather, transport, general"
    )
    destinations: list[str] = Field(
        description="Primary destinations mentioned or inferred (cities, regions, countries)"
    )
    dates: str = Field(
        description="Travel dates provided or inferred (e.g., '2025-10-12 to 2025-10-15', or 'unknown')"
    )
    duration_days: int | None = Field(
        default=None, description="Number of trip days if known or inferred"
    )
    budget_range: str | None = Field(
        default=None, description="Budget indication (e.g. 'USD 800–1200 total', 'unknown')"
    )

    summary: str = Field(
        description="A concise, traveler-friendly answer to the question."
    )

    itinerary: list[str] = Field(
        default_factory=list,
        description="If applicable, daily plan bullets (e.g., 'Day 1: Old Town walking tour...').",
    )

    recommendations: dict = Field(
        default_factory=dict,
        description=(
            "Curated suggestions. Keys can include: 'hotels', 'attractions', 'restaurants', "
            "'neighborhoods', 'tours', 'transport_options'. Each value should be a list of strings."
        ),
    )

    practical: dict = Field(
        default_factory=dict,
        description=(
            "Useful logistics and advisories. Keys may include: 'visa', 'entry_requirements', "
            "'safety', 'health', 'currency', 'tipping', 'local_sims_wifi', 'power_plugs', 'best_time_to_visit', 'weather'."
        ),
    )

    estimated_costs: dict = Field(
        default_factory=dict,
        description="If costs requested, provide a breakdown such as 'lodging', 'food', 'transport', 'activities' with numbers and currency if possible.",
    )

    sources: list[str] = Field(
        default_factory=list, description="URLs or titles of sources used."
    )
    tools_used: list[str] = Field(
        default_factory=list,
        description="Which tools were invoked (e.g., 'search', 'wikipedia', 'save_text_to_file').",
    )

# ----------------
# 3) Tools (search, wiki, save)
# ----------------
def save_to_txt(data: str, filename: str = "travel_output.txt"):
    """Saves structured travel data to a text file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Travel Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)
    return f"Data successfully saved to {filename}"

save_tool = Tool(
    name="save_text_to_file",
    func=save_to_txt,
    description="Saves structured travel data to a local text file.",
)

# Web search (DuckDuckGo) – great for official tourism, visa pages, transport schedules, etc.
search = DuckDuckGoSearchRun()
search_tool = Tool(
    name="search",
    func=search.run,
    description="Search the web for travel details like visa rules, local transport, attractions, official tourism info.",
)

# Wikipedia for quick destination overviews, landmarks, background
api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=1200)
wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)

tools = [search_tool, wiki_tool, save_tool]

# ----------------
# 4) LLM & Parser
# ----------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, api_key=api_key)
parser = PydanticOutputParser(pydantic_object=TravelResponse)

# ----------------
# 5) Prompt (TRAVEL-ONLY!)
# ----------------
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a meticulous, friendly TRAVEL AGENT assistant.
Your entire job is to answer ONLY travel-related questions: trip planning, destinations, itineraries, transport,
visas, entry requirements, budgets/costs, weather/seasonality, safety/health, attractions, hotels, restaurants,
neighborhoods, tours, packing, power plugs, connectivity, currencies, events/festivals, and local customs.

HARD RULES:
- If the user query is NOT about travel, politely refuse and explain you only handle travel details.
- When the query IS about travel, research as needed with the tools to give accurate, practical guidance.
- Prefer official or authoritative sources (government visa pages, official tourism boards, transit operators).
- If dates are missing, do not ask follow-ups; make reasonable assumptions and label them clearly.
- Give specific names where helpful (stations, neighborhoods, hotels, attractions, lines/routes).
- If costs are given, include currency symbols and ranges; otherwise state assumptions.
- Keep answers concise but actionable.
- ALWAYS output ONLY valid JSON that matches the schema below. No extra commentary.

Wrap the output STRICTLY in this format and provide no other text:
{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

# ----------------
# 6) Agent
# ----------------
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools
)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# ----------------
# 7) Run
# ----------------
# Example:
#   Query ideas:
#   - "Plan a 3-day itinerary for Kandy from Colombo in October with a mid-range budget."
#   - "Do I need a visa for Singapore if I have a Sri Lankan passport? Traveling in December."
#   - "What’s the best way to get from Paris CDG to the city center late at night?"
#
# Replace the input prompt below with any travel-related question.
query = input("Enter your travel question: ")

raw_response = agent_executor.invoke({"query": query})

# The AgentExecutor typically returns a dict with an 'output' key containing the model's text
model_output = None
if isinstance(raw_response, dict):
    if "output" in raw_response and isinstance(raw_response["output"], str):
        model_output = raw_response["output"]
    else:
        # Fallback: try to stringify the whole payload (in case a different return shape is used)
        model_output = str(raw_response)
else:

    model_output = str(raw_response)

# Parse to Pydantic object (or show a helpful error)
try:

    structured_response = parser.parse(model_output)
    print(structured_response.json(indent=2, ensure_ascii=False))
    
except Exception as e:
    print("Error parsing response:", e)
    print("Raw model output:")
    print(model_output)
