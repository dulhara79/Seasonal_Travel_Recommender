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
import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder

from server.schemas.global_schema import TravelState

# setup logger
logger = logging.getLogger(__name__)

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


# === NEW helper: compute confidence heuristic for a title ===
def _compute_confidence_for_title(title: str, docs: List, k: int = 5) -> float:
    """
    Simple heuristic: count how many of the top-k docs mention tokens from the title,
    then return (count / k). If no docs, return 0.0.
    Title tokens filtered to length > 3 to ignore small words.
    """
    if not title or not docs:
        return 0.0
    # prepare tokens from title
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    tokens = [t for t in cleaned.split() if len(t) > 3]
    if not tokens:
        # if no good tokens, try using the full title phrase match
        tokens = [title.lower()]

    check_k = min(k, len(docs))
    if check_k <= 0:
        return 0.0

    count = 0
    # check top-k docs (preserve original order)
    for d in docs[:check_k]:
        content = (d.page_content or "").lower()
        # match if any token found in doc text or full title phrase present
        if any(tok in content for tok in tokens) or title.lower() in content:
            count += 1
    return float(count) / float(check_k)


def suggest_activities(inp: dict) -> dict:
    """
    High-level entry point your orchestrator can call.
    Accepts either a dict or a pydantic-like object.
    Returns a dict matching the JSON shape expected by the orchestrator.
    """

    print(f"\nDEBUG: suggest_activities called with inp={inp}")

    # Ensure index + vectorstore available
    if not os.path.isdir(INDEX_DIR):
        print("[activity_agent] Index not found; building now (this may take a few minutes)...")
        build_or_refresh_index()

    vs = _load_vectorstore()
    llm = _llm()

    # Accept either a dict or a pydantic model-like object.
    def _get(key, default=None):
        try:
            if isinstance(inp, dict):
                return inp.get(key, default)
            return getattr(inp, key, default)
        except Exception:
            return default

    # Safe accessors
    destination = (_get("destination", "") or "").strip()
    suggest_locations = _get("suggest_locations", []) or []
    user_prefs = _get("user_preferences", None) or _get("preferences", None) or []
    prefs = ", ".join(user_prefs)

    # Build retriever context
    locs = _expand_locations(destination, suggest_locations)
    retriever = _retriever_for_location(vs, locs, llm)

    # Build a compact query (same logic you had originally)
    blocks = [
        f"Activities in/near {destination}" if destination else "Activities",
        f"Best things to do in {destination} for {(_get('type_of_trip') or 'travelers')}",
        f"Budget: {_get('budget','any')}; Season: {_get('season','any')}; Preferences: {prefs or 'any'}"
    ]
    if suggest_locations:
        blocks.append("Also consider: " + ", ".join(suggest_locations))
    query = " | ".join(blocks)

    # Retrieve docs (chunks)
    try:
        docs = retriever(query)
    except Exception as e:
        print(f"[activity_agent] Retriever failed: {e}")
        docs = []

    # Dates parsing (ensure dates always defined for fallback)
    try:
        start = datetime.strptime(_get("start_date"), "%Y-%m-%d") if _get("start_date") else datetime.today()
        end = datetime.strptime(_get("end_date"), "%Y-%m-%d") if _get("end_date") else start
    except Exception:
        start = datetime.today()
        end = start
    dates = _date_range(start, end)

    # Format context for LLM and extract provenance/top sources
    context = _format_context(docs)
    top_sources = _extract_top_sources(docs, k=3)

    # Build prompt text (serialize input safely)
    try:
        trip_json = json.dumps(jsonable_encoder(inp), indent=2, ensure_ascii=False)
    except Exception:
        # fallback to simple dict -> json
        trip_json = json.dumps(inp if isinstance(inp, dict) else str(inp), indent=2, ensure_ascii=False)

    prompt_text = BASE_SYSTEM + "\n\n" + PROMPT_INSTRUCTIONS.format(trip=trip_json, context=context)
    # Optionally append a short provenance hint for the LLM
    if top_sources:
        prompt_text += "\n\nTop sources used (for provenance):\n" + "\n".join(top_sources)

    print(f"[activity_agent] Calling LLM with prompt (truncated)...")
    # LLM call (attempt multiple variants for compatibility)
    from langchain.schema import HumanMessage

    text = ""
    try:
        response = llm.generate([[HumanMessage(content=prompt_text)]])
        gens = getattr(response, "generations", None)
        if isinstance(gens, list) and gens:
            first = gens[0]
            if isinstance(first, list) and first and hasattr(first[0], "text"):
                text = first[0].text
            else:
                text = str(first[0]) if first else str(response)
        else:
            text = getattr(response, "llm_output", {}).get("content", "") or str(response)
    except Exception as e:
        # fallbacks
        try:
            text = llm.predict(prompt_text)
        except Exception:
            try:
                res = llm([HumanMessage(content=prompt_text)])
                if isinstance(res, str):
                    text = res
                else:
                    text = getattr(res, "content", "") or getattr(res, "text", "") or str(res)
            except Exception as e2:
                text = ""
                print(f"[activity_agent] LLM calls failed: {e} | fallback: {e2}")

    # Defensive: if empty or whitespace, skip json.loads and go fallback
    if not isinstance(text, str) or not text.strip():
        logger.error("[activity_agent] LLM returned empty response; using fallback suggestions. Prompt (truncated): %s", prompt_text[:600])
        # build fallback day_plans using dates (guaranteed defined above)
        day_plans = []
        for d in dates:
            day_plans.append({
                "date": d.strftime("%Y-%m-%d"),
                "suggestions": [
                    {
                        "time_of_day": "morning",
                        "title": f"Explore around {destination or 'the area'}",
                        "why": "Nice light and cooler temps.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                    {
                        "time_of_day": "noon",
                        "title": "Local lunch & shorter indoor stop",
                        "why": "Avoid the heat.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                    {
                        "time_of_day": "evening",
                        "title": "Sunset viewpoint or market walk",
                        "why": "Golden hour and local vibes.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                    {
                        "time_of_day": "night",
                        "title": "Dinner / cultural show",
                        "why": "Relax and enjoy local cuisine/culture.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                ]
            })
        return {
            "destination": destination,
            "overall_theme": f"Activities near {destination}" if destination else "Suggested activities",
            "day_plans": day_plans,
            "notes": "LLM returned empty; provided fallback suggestions.",
            "status": "fallback",
            "top_sources": top_sources
        }

    # Try parse JSON from LLM response
    try:
        data = json.loads(text)
        # Attach status and provenance
        data["status"] = "complete"
        # add top_sources list into result if not present
        if "top_sources" not in data:
            data["top_sources"] = top_sources

        # Compute and attach confidence per suggestion
        try:
            # Determine k for heuristic: use up to 5 docs
            heuristic_k = min(5, max(1, len(docs)))
            for day in data.get("day_plans", []):
                suggestions = day.get("suggestions", [])
                for s in suggestions:
                    title = s.get("title", "") or ""
                    # simple heuristic: fraction of top-k docs that mention title tokens
                    heuristic = _compute_confidence_for_title(title, docs, k=heuristic_k)
                    # For LLM-produced items, ensure a conservative minimum of 0.8
                    confidence = max(heuristic, 0.8)
                    # clamp between 0 and 1
                    confidence = max(0.0, min(1.0, float(confidence)))
                    s["confidence"] = confidence
                    # ensure source_hints exists
                    if "source_hints" not in s:
                        s["source_hints"] = top_sources
        except Exception as ci_e:
            print(f"[activity_agent] Confidence assignment failed: {ci_e}")

        print(f"\nDEBUG: (try block) ACTIVITY AGENT LLM RAW RESPONSE parsed successfully.")
        return data
    except Exception as parse_exc:
        logger.error("[activity_agent] Could not parse LLM output as JSON: %s", parse_exc)
        logger.error("[activity_agent] Raw LLM text (truncated): %s", (text or "")[:2000])
        print(f"[activity_agent] Could not parse LLM output as JSON: {parse_exc}")
        print(f"[activity_agent] Raw LLM text (truncated): {text[:600]}")

        # fallback heuristic (use dates guaranteed to be set)
        day_plans = []
        for d in dates:
            day_plans.append({
                "date": d.strftime("%Y-%m-%d"),
                "suggestions": [
                    {
                        "time_of_day": "morning",
                        "title": f"Explore around {destination or 'the area'}",
                        "why": "Nice light and cooler temps.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                    {
                        "time_of_day": "noon",
                        "title": "Local lunch & shorter indoor stop",
                        "why": "Avoid the heat.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                    {
                        "time_of_day": "evening",
                        "title": "Sunset viewpoint or market walk",
                        "why": "Golden hour and local vibes.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                    {
                        "time_of_day": "night",
                        "title": "Dinner / cultural show",
                        "why": "Relax and enjoy local cuisine/culture.",
                        "source_hints": [],
                        "confidence": 0.3
                    },
                ]
            })

        return {
            "destination": destination,
            "overall_theme": f"Activities near {destination}" if destination else "Suggested activities",
            "day_plans": day_plans,
            "notes": "LLM returned non-JSON; provided fallback suggestions.",
            "status": "fallback",
            "top_sources": top_sources
        }


# # CLI entry: build index if script run directly
# if __name__ == "__main__":
#     print("Building / refreshing FAISS index for activity retrieval...")
#     build_or_refresh_index()
#     print("Done.")
