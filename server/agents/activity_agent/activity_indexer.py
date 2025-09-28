# server/agents/activity_agent/activity_indexer.py
"""
Builds a FAISS index from website sources and provides a suggest_activities()
function that performs retrieval + LLM synthesis to produce per-day time-slot
activity plans.

Usage:
  1. Ensure OPENAI_API_KEY is set in your environment (e.g. export/setx).
  2. Install dependencies (see instructions below).
  3. Build index: `python -m server.agents.activity_agent.activity_indexer`
  4. In your workflow, call `suggest_activities(activity_input_dict_or_pydantic_model)`.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder

from server.schemas.global_schema import TravelState

# load .env from the project root
load_dotenv()

# quick sanity check (optional, remove later)
print("USER_AGENT loaded as:", os.getenv("USER_AGENT"))

# LangChain / community components
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Embeddings & LLM (modern imports)
from langchain_openai import OpenAIEmbeddings, ChatOpenAI


# FAISS import compatibility (community vs core)
try:
    from langchain_community.vectorstores import FAISS
except Exception:
    from langchain.vectorstores import FAISS

# # Embeddings & LLM
# try:
#     from langchain_openai import OpenAIEmbeddings
# except Exception:
#     # fallback import path
#     from langchain_openai import OpenAIEmbeddings

# try:
#     # from langchain_community.chat_models import ChatOpenAI
#     from langchain_openai import ChatOpenAI
# except Exception:
#     from langchain.chat_models import ChatOpenAI

# MultiQuery retriever (improves recall by paraphrasing queries)
try:
    from langchain.retrievers.multi_query import MultiQueryRetriever
except Exception:
    # Some versions expose MultiQueryRetriever from different path
    try:
        from langchain.retrievers import MultiQueryRetriever
    except Exception:
        MultiQueryRetriever = None

# Your project config & sources
try:
    from server.utils.config import (
        OPENAI_API_KEY,
        OPENAI_MODEL,
        ACTIVITY_FAISS_DIR,
        ACTIVITY_SOURCES_JSON,
    )
except Exception:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    ACTIVITY_FAISS_DIR = os.getenv("ACTIVITY_FAISS_DIR", "server/data/activity_faiss")
    ACTIVITY_SOURCES_JSON = os.getenv("ACTIVITY_SOURCES_JSON", "server/data/activity_sources.json")

# Where to read default sources from
try:
    from server.agents.activity_agent.activity_sources import default_sources
except Exception:
    # fallback empty
    default_sources = []

INDEX_DIR = ACTIVITY_FAISS_DIR
SOURCES_JSON = ACTIVITY_SOURCES_JSON


def _save_sources(sources: List[str]):
    os.makedirs(os.path.dirname(SOURCES_JSON), exist_ok=True)
    with open(SOURCES_JSON, "w", encoding="utf-8") as f:
        json.dump({"sources": sources}, f, ensure_ascii=False, indent=2)


def _load_sources() -> List[str]:
    if os.path.exists(SOURCES_JSON):
        with open(SOURCES_JSON, "r", encoding="utf-8") as f:
            return json.load(f).get("sources", default_sources)
    return default_sources


def build_or_refresh_index(sources: Optional[List[str]] = None) -> str:
    """
    Fetch pages from `sources` (or stored sources), split into chunks, embed
    them using OpenAI embeddings, and save a FAISS index to disk.
    Returns the path to the saved index.
    """
    if not sources:
        sources = _load_sources()
    else:
        _save_sources(sources)

    print(f"[indexer] Loading {len(sources)} sources...")
    loader = WebBaseLoader(sources)
    docs = loader.load()  # list of langchain Document objects
    print(f"[indexer] Loaded {len(docs)} documents from web.")

    # Attach source url and lightweight tags (heuristic) for later filtering
    for d in docs:
        meta = d.metadata or {}
        src = meta.get("source") or meta.get("url") or ""
        meta["source"] = src
        url_low = (src or "").lower()
        tags = set(meta.get("tags", []))
        for loc in ("kandy", "galle", "ella", "sigiriya", "colombo", "mirissa", "trincomalee"):
            if loc in url_low:
                tags.add(loc)
        meta["tags"] = list(tags)
        d.metadata = meta

    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    print(f"[indexer] Split into {len(chunks)} chunks.")

    # add heuristic tags to chunk metadata based on content
    for c in chunks:
        meta = c.metadata or {}
        text_low = c.page_content.lower()
        loc_tags = []
        for loc in ("kandy", "ella", "sigiriya", "galle", "colombo", "mirissa", "trincomalee"):
            if loc in text_low:
                loc_tags.append(loc)
        if loc_tags:
            current = set(meta.get("tags", []))
            meta["tags"] = list(current.union(set(loc_tags)))
            c.metadata = meta

    # Build embeddings + FAISS
    print("[indexer] Creating embeddings (OpenAI)...")
    emb_kwargs = {}
    # Try both param names in case of different langchain versions
    try:
        embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    except TypeError:
        embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    vs = FAISS.from_documents(chunks, embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    vs.save_local(INDEX_DIR)
    print(f"[indexer] Saved FAISS index to: {INDEX_DIR}")
    return INDEX_DIR


def _load_vectorstore() -> FAISS:
    """
    Load the locally persisted FAISS index (must exist).
    """
    try:
        emb_kwargs = {}
        try:
            embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        except TypeError:
            embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        return FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        raise RuntimeError(f"Could not load FAISS index: {e}. Run build_or_refresh_index() first.")


def _date_range(start: datetime, end: datetime):
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def _expand_locations(primary: str, suggest_locations: Optional[List[str]]):
    names = [primary.strip().lower()] if primary else []
    if suggest_locations:
        for s in suggest_locations:
            n = s.strip().lower()
            if n and n not in names:
                names.append(n)
    return names or [primary.strip().lower()]


def _retriever_for_location(vs: FAISS, locs: List[str], llm: ChatOpenAI):
    """
    Returns a retrieval function that uses a MultiQueryRetriever (if available)
    to produce a list of relevant Document objects (chunks).
    """
    base_ret = vs.as_retriever(search_type="mmr", search_kwargs={"k": 8, "fetch_k": 32})
    if MultiQueryRetriever is not None:
        mqr = MultiQueryRetriever.from_llm(retriever=base_ret, llm=llm)
    else:
        mqr = None

    def retrieve(query: str):
        if mqr:
            docs = mqr.invoke(query)
        else:
            docs = base_ret.invoke(query)

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


def _llm():
    try:
        return ChatOpenAI(openai_api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.2)
    except TypeError:
        return ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.2)


# A lightweight prompt assembler for the LLM (system + task instructions)
BASE_SYSTEM = (
    "You are ActivityAgent, a travel activity planner for Sri Lanka. "
    "Given retrieved web snippets and the user's trip details, produce practical, recent-feeling suggestions. "
    "Create a per-day plan with four slots: morning, noon, evening, night. "
    "Tailor to season, budget, group size, and preferences."
)

PROMPT_INSTRUCTIONS = (
    "Rules:\n"
    "- Prefer activities close to the provided location(s).\n"
    "- Morning: outdoor/hikes/sightseeing; Noon: indoor/food/rest/museums; "
    "Evening: sunset/views/markets; Night: dinners/cultural shows/stargazing.\n"
    "- If weather risk (monsoon/season) suggest safer alternatives.\n"
    "- Keep each suggestion concise: a short title and a one-sentence why.\n"
    "- Include light source hints when possible (host/domain).\n\n"
    "Input trip JSON:\n{trip}\n\n"
    "Top-k retrieved context (truncated):\n{context}\n\n"
    "Return **strict JSON** with this shape:\n"
    '{{\n  "destination": string,\n  "overall_theme": string,\n  "day_plans": [\n    {{\n      "date": "YYYY-MM-DD",\n      "suggestions": [\n        {{ "time_of_day":"morning|noon|evening|night", "title": string, "why": string, "source_hints":[string] }}\n      ]\n    }}\n  ],\n  "notes": string\n}}\n'
)


def _format_context(docs, max_chars: int = 2400) -> str:
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


# === NEW helper: extract top-k sources for provenance ===
def _extract_top_sources(docs: List, k: int = 3) -> List[str]:
    """
    Return the top-k distinct source URLs encountered in docs (preserve order).
    """
    sources = []
    for d in docs:
        meta = d.metadata or {}
        src = meta.get("source") or meta.get("url") or ""
        if src:
            # keep uniqueness, preserve first-seen order
            if src not in sources:
                sources.append(src)
        if len(sources) >= k:
            break
    return sources

def suggest_activities(inp: dict) -> dict:
    """
    High-level entry point your orchestrator can call.
    `inp` should be a dict with keys (similar to ActivityAgentInput):
      - destination (string)
      - start_date (YYYY-MM-DD) optional
      - end_date (YYYY-MM-DD) optional
      - user_preferences (list of strings) optional
      - budget, type_of_trip, no_of_traveler, season, suggest_locations (list) etc.

    Returns a dict matching the JSON shape in the prompt above.
    """

    print(f"\nDEBUG: suggest_activities called with inp={inp}")

    # if not os.path.isdir(INDEX_DIR):
    #     print("[activity_agent] Index not found; building now (this may take a few minutes)...")
    #     build_or_refresh_index()

    # vs = _load_vectorstore()
    # llm = _llm()

    # destination = inp.destination  or ""
    # suggest_locations = inp.locations_to_visit or []
    # locs = _expand_locations(destination, suggest_locations)
    # retriever = _retriever_for_location(vs, locs, llm)

    # # Build a compact query
    # prefs = ", ".join(inp.user_preferences or [])
    # blocks = [
    #     f"Activities in/near {destination}",
    #     f"Best things to do in {destination} for {inp.type_of_trip, inp.no_of_traveler}",
    #     f"Budget: {inp.budget,'any'}; Season: {inp.season,any}; Preferences: {prefs or 'any'}"
    # ]
    # if suggest_locations:
    #     blocks.append("Also consider: " + ", ".join(suggest_locations))
    # query = " | ".join(blocks)

    # docs = retriever(query)

    # # Format dates
    # try:
    #     start = datetime.strptime(inp.start_date, "%Y-%m-%d") if inp.start_date else datetime.today()
    #     end = datetime.strptime(inp.end_date, "%Y-%m-%d") if inp.end_date else start
    # except Exception:
    #     start = datetime.today()
    #     end = start
    # dates = _date_range(start, end)

    # context = _format_context(docs)

    # # Convert inp to a JSON-serializable structure before dumping
    # trip_json = json.dumps(jsonable_encoder(inp), indent=2, ensure_ascii=False)
    # prompt_text = BASE_SYSTEM + "\n\n" + PROMPT_INSTRUCTIONS.format(trip=trip_json, context=context)


        # --- start replacement block ---
    if not os.path.isdir(INDEX_DIR):
        print("[activity_agent] Index not found; building now (this may take a few minutes)...")
        build_or_refresh_index()

    vs = _load_vectorstore()
    llm = _llm()

    # Accept either a dict or a pydantic model-like object.
    # Use .get when available; otherwise fallback to attribute access.
    def _get(key, default=None):
        try:
            if isinstance(inp, dict):
                return inp.get(key, default)
            # pydantic model or object with attributes
            return getattr(inp, key, default)
        except Exception:
            return default

    # Use safe accessors
    destination = _get("destination", "") or ""
    suggest_locations = _get("suggest_locations", []) or []
    # allow older name variants
    user_prefs = _get("user_preferences", None) or _get("preferences", None) or []
    locs = _expand_locations(destination, suggest_locations)

    # Build retriever using llm object (some code expects llm param)
    retriever = _retriever_for_location(vs, locs, llm)






    # --- LLM call: use proper LangChain message objects (HumanMessage) ---
    from langchain.schema import HumanMessage

    print("[activity_agent] Calling LLM with prompt (truncated)...")
    text = ""

    # Primary attempt: use generate with a nested list of HumanMessage objects
    try:
        response = llm.generate([[HumanMessage(content=prompt_text)]])
        gens = getattr(response, "generations", None)
        if isinstance(gens, list) and gens:
            first = gens[0]
            # gens[0] is usually a list of Generation objects
            if isinstance(first, list) and first and hasattr(first[0], "text"):
                text = first[0].text
            else:
                text = str(first[0]) if first else str(response)
        else:
            # fallback: try older .llm_output or string form
            text = getattr(response, "llm_output", {}).get("content", "") or str(response)
    except Exception as e:
        # If generate fails for this version, try calling the model directly
        try:
            # Many Chat models support __call__ or .predict
            text = llm.predict(prompt_text)  # best-effort; may raise if not supported
        except Exception:
            try:
                # final fallback: try calling llm as a callable with a HumanMessage
                res = llm([HumanMessage(content=prompt_text)])
                # res could be a string or a ChatResult-like object
                if isinstance(res, str):
                    text = res
                else:
                    # attempt to extract typical attributes
                    text = getattr(res, "content", "") or getattr(res, "text", "") or str(res)
            except Exception as e2:
                # If all attempts fail, surface a clear message for debugging
                text = f"LLM call failed: {e} | fallback error: {e2}"




    # Attempt to parse JSON
    try:
        data = json.loads(text)
        data["status"] = "complete"
        print(f"\nDEBUG: (try block) ACTIVITY AGENT LLM RAW RESPONSE: {data}")
        return data
    except Exception:
        # fallback heuristic: create minimal day_plans
        day_plans = []
        for d in dates:
            day_plans.append({
                "date": d.strftime("%Y-%m-%d"),
                "suggestions": [
                    {"time_of_day": "morning", "title": f"Explore around {destination}", "why": "Nice light and cooler temps.", "source_hints": []},
                    {"time_of_day": "noon", "title": "Local lunch & shorter indoor stop", "why": "Avoid heat.", "source_hints": []},
                    {"time_of_day": "evening", "title": "Sunset viewpoint or market walk", "why": "Golden hour and vibes.", "source_hints": []},
                    {"time_of_day": "night", "title": "Dinner / cultural show", "why": "Relax and enjoy local cuisine/culture.", "source_hints": []},
                ]
            })
        print(f"\nDEBUG: (exception block) ACTIVITY AGENT LLM RAW RESPONSE: {day_plans, text}")
        return {
            "destination": destination,
            "overall_theme": f"Activities near {destination}",
            "day_plans": day_plans,
            "notes": "LLM returned non-JSON; provided fallback suggestions.",
            "status": "fallback"
        }

# CLI entry: build index if script run directly
if __name__ == "__main__":
    print("Building / refreshing FAISS index for activity retrieval...")
    build_or_refresh_index()
    print("Done.")