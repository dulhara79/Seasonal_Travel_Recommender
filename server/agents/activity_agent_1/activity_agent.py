import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

# LangChain bits
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain.retrievers.multi_query import MultiQueryRetriever

from server.agents.activity_agent_1.rag_source_URLs import DEFAULT_SOURCES
from server.schemas.activity_schemas import ActivityAgentInput, ActivityAgentOutput, DayPlan, TimeSlotSuggestion

# Reuse your config
try:
    from server.utils.config import OPENAI_API_KEY, LLM_MODEL, ACTIVITY_FAISS_DIR, ACTIVITY_SOURCES_JSON
except Exception:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

INDEX_DIR = ACTIVITY_FAISS_DIR
SOURCES_JSON = ACTIVITY_SOURCES_JSON

def _save_sources(sources: List[str]):
    os.makedirs(os.path.dirname(SOURCES_JSON), exist_ok=True)
    with open(SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump({"sources": sources}, f, ensure_ascii=False, indent=2)


def _load_sources() -> List[str]:
    if os.path.exists(SOURCES_JSON):
        with open(SOURCES_JSON, "r", encoding="utf-8") as f:
            return json.load(f).get("sources", DEFAULT_SOURCES)
    return DEFAULT_SOURCES


def build_or_refresh_index(sources: Optional[List[str]] = None) -> str:
    """Fetch pages, split, embed, build FAISS index and persist to disk.
    Returns the index directory path.
    """
    if not sources:
        sources = _load_sources()
    else:
        _save_sources(sources)

    loader = WebBaseLoader(sources)
    docs: List[Document] = loader.load()

    # Attach simple location guesses from URLs for later filtering
    for d in docs:
        meta = d.metadata or {}
        meta.setdefault("source", meta.get("source") or meta.get("url"))
        # heuristic tags
        url = (meta.get("source") or "").lower()
        tags = []
        if "kandy" in url: tags.append("kandy")
        if "sigiriya" in url: tags.append("sigiriya")
        if "ella" in url: tags.append("ella")
        if "galle" in url: tags.append("galle")
        if "colombo" in url: tags.append("colombo")
        meta["tags"] = list(set(tags))
        d.metadata = meta

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    # Add more fine-grained tags based on text content (very light heuristic)
    for c in chunks:
        meta = c.metadata or {}
        text_low = c.page_content.lower()
        loc_tags = []
        for loc in ["meemure", "kandy", "ella", "sigiriya", "nuwara", "galle", "colombo", "mirissa", "trincomalee",
                    "anuradhapura", "polonnaruwa"]:
            if loc in text_low:
                loc_tags.append(loc)
        if loc_tags:
            current = set(meta.get("tags", []))
            meta["tags"] = list(current.union(set(loc_tags)))
            c.metadata = meta

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    vs = FAISS.from_documents(chunks, embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    vs.save_local(INDEX_DIR)
    return INDEX_DIR


def _load_vectorstore() -> FAISS:
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    return FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)


# Core RAG Suggestion Logic
def _date_range(start: datetime, end: datetime) -> List[datetime]:
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def _expand_locations(primary: str, suggest_locations: List[str]) -> List[str]:
    names = [primary.strip().lower()]
    for s in suggest_locations:
        n = s.strip().lower()
        if n and n not in names:
            names.append(n)
    return names


def _build_query_blocks(inp: ActivityAgentInput) -> List[str]:
    prefs = ", ".join(inp.user_preferences or inp.preferences or [])
    blocks = [
        f"Activities in/near {inp.destination}",
        f"Best things to do in {inp.destination} for {inp.type_of_trip or 'travelers'}",
        f"Budget: {inp.budget or 'any'}; Season: {inp.season or 'any'}; Preferences: {prefs or 'any'}",
    ]
    if inp.suggest_locations:
        more = ", ".join(inp.suggest_locations)
        blocks.append(f"Also consider: {more}")
    return blocks


def _retriever_for_location(vs: FAISS, locs: List[str], llm: ChatOpenAI):
    # MultiQueryRetriever makes a few paraphrased queries for richer recall
    base_ret = vs.as_retriever(search_type="mmr", search_kwargs={"k": 8, "fetch_k": 32})
    mqr = MultiQueryRetriever.from_llm(retriever=base_ret, llm=llm)

    def retrieve(query: str):
        docs = mqr.get_relevant_documents(query)
        # Light location filter by tag presence or substring match
        keep = []
        for d in docs:
            tags = [t.lower() for t in (d.metadata or {}).get("tags", [])]
            txt = d.page_content.lower()
            if any(l in tags for l in locs) or any(l in txt for l in locs):
                keep.append(d)
        # fallback if too strict
        return keep or docs

    return retrieve


def _llm() -> ChatOpenAI:
    return ChatOpenAI(api_key=OPENAI_API_KEY, model=LLM_MODEL, temperature=0.3)

SUGGEST_PROMPT = ChatPromptTemplate.from_messages([
    ("system", (
        "You are ActivityAgent, a travel activity planner for Sri Lanka. "
        "Given retrieved web snippets and the user's trip details, produce practical, recent-feeling suggestions. "
        "Create a per-day plan with four slots: morning, noon, evening, night. "
        "Tailor to season, budget, group size, and preferences."
    )),
    ("system", (
        "Rules: \n"
        "- Prefer activities close to the provided location(s).\n"
        "- Morning: nature/hikes/sightseeing; Noon: indoor/food/museums/rest; "
        "  Evening: sunset/markets/relaxed tours; Night: dinners/cultural shows/stargazing.\n"
        "- If weather risk in season (e.g., monsoon), suggest alternatives.\n"
        "- Keep each suggestion concise: a short title and a one-sentence why.\n"
        "- When relevant, include brief source hints (URL host or page title)."
    )),
    ("human", (
        "Trip JSON:\n{trip}\n\n"
        "Top-k retrieved context (truncated):\n{context}\n\n"
        "Now produce JSON with this shape strictly:\n"
        "{{{{\n  \"destination\": string,\n  \"overall_theme\": string,\n  \"day_plans\": [\n    {{{{\n      \"date\": \"YYYY-MM-DD\",\n      \"suggestions\": [\n        {{{{\n          \"time_of_day\": \"morning|noon|evening|night\",\n          \"title\": string,\n          \"why\": string,\n          \"source_hints\": [string]\n        }}}}\n      ]\n    }}}}\n  ],\n  \"notes\": string\n}}}}\n"
    )),
])


def _format_context(docs: List[Document], max_chars: int = 2400) -> str:
    out = []
    used = 0
    for d in docs:
        src = (d.metadata or {}).get("source", "")
        chunk = d.page_content.strip().replace("\n", " ")
        piece = f"[Source: {src}]\n{chunk}\n"
        if used + len(piece) > max_chars:
            break
        out.append(piece)
        used += len(piece)
    return "\n".join(out)


def suggest_activities(inp: ActivityAgentInput) -> ActivityAgentOutput:
    if not os.path.isdir(INDEX_DIR):
        # Build index on first run
        build_or_refresh_index()

    print(f"Activity agent input: {inp}")

    vs = _load_vectorstore()
    llm = _llm()

    locs = _expand_locations(inp.destination, inp.suggest_locations)
    retrieve = _retriever_for_location(vs, locs, llm)

    # Compose a query string from the input
    blocks = _build_query_blocks(inp)
    query = " | ".join(blocks)

    # Retrieve docs
    docs = retrieve(query)

    # If dates missing, assume 1 day plan
    try:
        start = datetime.strptime(inp.start_date, "%Y-%m-%d") if inp.start_date else datetime.today()
        end = datetime.strptime(inp.end_date, "%Y-%m-%d") if inp.end_date else start
    except ValueError:
        start = datetime.today()
        end = start

    dates = _date_range(start, end)

    # Build LLM call
    context = _format_context(docs)

    trip_json = json.dumps(inp.model_dump(), indent=2)
    prompt = SUGGEST_PROMPT.format_messages(trip=trip_json, context=context)

    raw = llm.invoke(prompt)
    text = raw.content if hasattr(raw, "content") else str(raw)

    # Try to parse into pydantic output
    try:
        data = json.loads(text)
        return ActivityAgentOutput(**data)
    except Exception:
        # If LLM returned non-JSON, create a minimal fallback using heuristics
        day_plans: List[DayPlan] = []
        for d in dates:
            day_plans.append(DayPlan(
                date=d.strftime("%Y-%m-%d"),
                suggestions=[
                    TimeSlotSuggestion(time_of_day="morning", title=f"Explore around {inp.destination}",
                                       why="Good light and cooler temps.", source_hints=[]),
                    TimeSlotSuggestion(time_of_day="noon", title="Local lunch & short indoor stop",
                                       why="Heat avoidance.", source_hints=[]),
                    TimeSlotSuggestion(time_of_day="evening", title="Sunset viewpoint or village walk",
                                       why="Golden hour views.", source_hints=[]),
                    TimeSlotSuggestion(time_of_day="night", title="Dinner / cultural show", why="End the day relaxed.",
                                       source_hints=[]),
                ],
            ))
        return ActivityAgentOutput(
            destination=inp.destination,
            overall_theme=f"Activities near {inp.destination} tailored to {inp.type_of_trip or 'your trip'}",
            day_plans=day_plans,
            notes="LLM returned non-JSON; provided fallback suggestions.",
            season=inp.season,
            start_date=inp.start_date,
            end_date=inp.end_date,
            preferences=inp.preferences,
            no_of_traveler=inp.no_of_traveler,
            budget=inp.budget,
            user_preferences=inp.user_preferences,
            type_of_trip=inp.type_of_trip,
            suggest_locations=inp.suggest_locations,
            additional_info=inp.additional_info,
            status="completed",
        )
