# Paste this entire file contents (replace the previous activity_indexer.py)

# server/agents/activity_agent/activity_indexer.py
"""
Builds a FAISS index from website sources and provides a suggest_activities()
function that performs retrieval + LLM synthesis to produce per-day time-slot
activity plans.
...
(usage text omitted here for brevity; keep your original header)
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
    if not sources:
        sources = _load_sources()
    else:
        _save_sources(sources)

    print(f"[indexer] Loading {len(sources)} sources...")
    loader = WebBaseLoader(sources)
    docs = loader.load()
    print(f"[indexer] Loaded {len(docs)} documents from web.")

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

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
    chunks = splitter.split_documents(docs)
    print(f"[indexer] Split into {len(chunks)} chunks.")

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

    print("[indexer] Creating embeddings (OpenAI)...")
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
    try:
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
    names = []
    def add_name(s):
        if not s:
            return
        n = s.strip().lower()
        if n and n not in names:
            names.append(n)

    add_name(primary)
    if suggest_locations:
        for s in suggest_locations:
            add_name(s)

    tokens = []
    for n in list(names):
        for tok in re.split(r"[\s,/_\-]+", n):
            tok = tok.strip()
            if tok and tok not in names:
                tokens.append(tok)
    for t in tokens:
        add_name(t)

    return names or [primary.strip().lower()] if primary else []


def _retriever_for_location(vs: FAISS, locs: List[str], llm: ChatOpenAI, top_k: int = 12):
    k = max(8, top_k)
    base_ret = vs.as_retriever(search_type="mmr", search_kwargs={"k": k, "fetch_k": max(64, k*4)})
    if MultiQueryRetriever is not None:
        mqr = MultiQueryRetriever.from_llm(retriever=base_ret, llm=llm)
    else:
        mqr = None

    def retrieve(query: str):
        if mqr:
            docs = mqr.invoke(query)
        else:
            docs = base_ret.invoke(query)

        loc_tokens = [l.lower() for l in (locs or []) if l]
        keep = []
        fallback = []
        for d in docs:
            meta = d.metadata or {}
            tags = [t.lower() for t in meta.get("tags", [])]
            txt = (d.page_content or "").lower()
            src = (meta.get("source") or meta.get("url") or "").lower()

            strong = False
            if any(any(tok in tag for tag in tags) for tok in loc_tokens):
                strong = True
            if any(tok in txt for tok in loc_tokens):
                strong = True
            if any(tok in src for tok in loc_tokens):
                strong = True

            if strong:
                keep.append(d)
            else:
                fallback.append(d)

        if keep:
            return keep
        return docs

    return retrieve


def _llm():
    try:
        return ChatOpenAI(openai_api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.2)
    except TypeError:
        return ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0.2)


BASE_SYSTEM = (
    "You are ActivityAgent, a travel activity planner for Sri Lanka. "
    "Given retrieved web snippets and the user's trip details, produce practical, recent-feeling suggestions. "
    "Create a per-day plan with four slots: morning, noon, evening, night. "
    "Tailor to season, budget, group size, and preferences."
)

PROMPT_INSTRUCTIONS = (
    "IMPORTANT RULES (ENFORCE EXACT OUTPUT):\n"
    "- You MUST return exactly one `day_plans` entry per date contained in the Input trip JSON. "
    "If the trip spans N distinct dates, output N day_plans entries in the same chronological order.\n"
    "- Each day_plans entry MUST contain up to four suggestions mapped to time_of_day values: morning, noon, evening, night. "
    "If a slot is unavailable, return an explicit placeholder suggestion (title + why).\n"
    "- Prefer activities located as close as possible to the provided destination(s). If you are uncertain about distance, indicate low confidence in the suggestion.\n"
    "- Return STRICT JSON only, with the schema below. Do not output any narrative text outside the JSON.\n\n"
    "Input trip JSON:\n{trip}\n\n"
    "Top-k retrieved context (truncated):\n{context}\n\n"
    "Return **strict JSON** with this shape:\n"
    '{{\n  "destination": string,\n  "overall_theme": string,\n  "day_plans": [\n    {{\n      "date": "YYYY-MM-DD",\n      "suggestions": [\n        {{ "time_of_day":"morning|noon|evening|night", "title": string, "why": string, "source_hints":[string], "price_level":"low|medium|high", "confidence": number }}\n      ]\n    }}\n  ],\n  "notes": string\n}}\n'
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


def _extract_top_sources(docs: List, k: int = 3) -> List[str]:
    sources = []
    for d in docs:
        meta = d.metadata or {}
        src = meta.get("source") or meta.get("url") or ""
        if not src:
            continue
        # prefer non-llm_generated sources
        if "llm_generated" in src:
            continue
        if src not in sources:
            sources.append(src)
        if len(sources) >= k:
            break
    # if none found, fall back to llm_generated sources
    if not sources:
        for d in docs:
            src = (d.metadata or {}).get("source","")
            if src and src not in sources:
                sources.append(src)
            if len(sources) >= k:
                break
    return sources



def _compute_confidence_for_title(title: str, docs: List, k: int = 5) -> float:
    if not title or not docs:
        return 0.0
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    tokens = [t for t in cleaned.split() if len(t) > 3]
    if not tokens:
        tokens = [title.lower()]

    check_k = min(k, len(docs))
    if check_k <= 0:
        return 0.0

    count = 0
    for d in docs[:check_k]:
        content = (d.page_content or "").lower()
        if any(tok in content for tok in tokens) or title.lower() in content:
            count += 1
    return float(count) / float(check_k)


def _estimate_price_level(title: str, why: str, docs: List, user_budget: Optional[str] = None) -> str:
    text = f"{(title or '')} {(why or '')}".lower()
    low_kw = ("free", "walk", "hike", "market", "street food", "beach", "temple", "public", "park", "local eatery")
    high_kw = ("rooftop", "fine dining", "spa", "luxury", "private", "exclusive", "guided tour", "paid tour", "ticket", "entrance fee")
    for kw in low_kw:
        if kw in text:
            return "low"
    for kw in high_kw:
        if kw in text:
            return "high"
    if isinstance(user_budget, str):
        ub = user_budget.strip().lower()
        if ub in ("low", "medium", "high"):
            return ub
    return "medium"


def _is_outdoor_activity(title: str, why: str) -> bool:
    text = f"{(title or '')} {(why or '')}".lower()
    outdoor_kw = (
        "hike", "trek", "beach", "waterfall", "viewpoint", "sunset",
        "walk", "wild", "safari", "trekking", "cycling", "boat",
        "rafting", "snorkel", "surf", "climb", "mountain", "hiking"
    )
    return any(kw in text for kw in outdoor_kw)


def _seasonal_risk_for_location(location: str, date: datetime) -> bool:
    try:
        from server.agents.weather_agent import get_weather_forecast  # type: ignore
        try:
            forecast = get_weather_forecast(location, date)
            if isinstance(forecast, dict):
                prob = forecast.get("rain_probability") or forecast.get("precipitation_probability") or forecast.get("precip_prob")
                if isinstance(prob, (int, float)):
                    return float(prob) >= 0.4
                summary = str(forecast.get("summary", "") or forecast.get("weather", "")).lower()
                if any(r in summary for r in ("rain", "shower", "storm", "thunder", "wet")):
                    return True
        except Exception:
            pass
    except Exception:
        pass

    month = date.month
    wet_months_general = {4, 5, 10, 11}
    if month in wet_months_general:
        return True

    loc_low = (location or "").lower()
    if "trincomalee" in loc_low or "east" in loc_low:
        if month in {12, 1, 2}:
            return True

    return False


def _suggest_alternatives_for_activity(title: str) -> List[str]:
    text = (title or "").lower()
    if "hike" in text or "trek" in text or "mountain" in text:
        return ["Visit a tea factory / factory tour", "Explore a covered local market or museum"]
    if "beach" in text or "snorkel" in text or "surf" in text:
        return ["Visit an indoor aquarium or marine museum", "Relax at a local cafe or indoor cultural show"]
    if "waterfall" in text or "river" in text or "boat" in text:
        return ["Visit a nearby museum or botanical garden", "Take a cooking class or tea tasting session"]
    if "sunset" in text or "viewpoint" in text:
        return ["Explore a nearby indoor market or craft centre", "Visit the Royal Botanical Gardens or a tea factory tour"]
    return ["Visit a museum or cultural center", "Take a local cooking class or tea tasting", "Explore covered local markets"]


# single cache path (no duplicates)
_GENERATED_CACHE = os.path.join(os.path.dirname(INDEX_DIR), "generated_local_cache.json")


def _load_generated_cache():
    try:
        if os.path.exists(_GENERATED_CACHE):
            with open(_GENERATED_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_generated_cache(cache: dict):
    try:
        os.makedirs(os.path.dirname(_GENERATED_CACHE), exist_ok=True)
        with open(_GENERATED_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _llm_fetch_local_activities(location: str, prefs: str, num_days: int = 3, items_per_day: int = 4, llm_model=None):
    key = f"{location}||{prefs}||{num_days}||{items_per_day}"
    cache = _load_generated_cache()
    if key in cache:
        return cache[key]

    if not llm_model:
        llm_model = _llm()

    prompt = (
    "You are a travel assistant. The user asked for activities near a specific location. "
    "IMPORTANT: Only produce activities that are in or immediately surrounding the exact location given below. "
    "Do NOT list activities or places in other towns or regions. If you are unsure whether a place is in that town, "
    "set source_hint to 'local knowledge / estimate' and do NOT name a different town. Be conservative.\n\n"
    "Return ONLY a JSON array of objects. Each object must have:\n"
    "  date_offset (integer, 0 means first trip day),\n"
    "  time_of_day (one of morning|noon|evening|night),\n"
    "  title (string),\n"
    "  why (one short sentence),\n"
    "  source_hint (string),\n"
    "  price_level (one of low|medium|high)\n\n"
    f"Constraints:\n- Provide roughly {items_per_day * num_days} items spread across offsets 0..{num_days-1}.\n"
    "- If unsure about exact local facts, explicitly use source_hint: 'local knowledge / estimate'.\n"
    "- DO NOT mention towns other than: {location}\n"
    "- Do not output narrative outside the JSON.\n\n"
    f"Location: {location}\nPreferences: {prefs or 'none'}\nnum_days: {num_days}\nitems_per_day: {items_per_day}\n\nOutput JSON now:"
)


    text = ""
    try:
        from langchain.schema import HumanMessage
        resp = llm_model.generate([[HumanMessage(content=prompt)]])
        gens = getattr(resp, "generations", None)
        if isinstance(gens, list) and gens:
            first = gens[0]
            if isinstance(first, list) and first and hasattr(first[0], "text"):
                text = first[0].text
            else:
                text = str(first[0]) if first else str(resp)
        else:
            text = getattr(resp, "llm_output", {}).get("content", "") or str(resp)
    except Exception:
        try:
            text = llm_model.predict(prompt)
        except Exception:
            try:
                from langchain.schema import HumanMessage
                res = llm_model([HumanMessage(content=prompt)])
                text = getattr(res, "content", "") or getattr(res, "text", "") or str(res)
            except Exception:
                text = ""

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and all(isinstance(p, dict) for p in parsed):
            cache[key] = parsed
            _save_generated_cache(cache)
            return parsed
    except Exception:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                # remove first fence(s)
                cleaned = cleaned.split("```", 2)[-1]
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                cache[key] = parsed
                _save_generated_cache(cache)
                return parsed
        except Exception:
            pass

    return []


def suggest_activities(inp: dict) -> dict:
    print(f"\nDEBUG: suggest_activities called with inp={inp}")

    if not os.path.isdir(INDEX_DIR):
        print("[activity_agent] Index not found; building now (this may take a few minutes)...")
        build_or_refresh_index()

    vs = _load_vectorstore()
    llm = _llm()

    def _get(key, default=None):
        try:
            if isinstance(inp, dict):
                return inp.get(key, default)
            return getattr(inp, key, default)
        except Exception:
            return default

    destination = (_get("destination", "") or "").strip()
    suggest_locations = _get("suggest_locations", []) or []
    user_prefs = _get("user_preferences", None) or _get("preferences", None) or []
    prefs = ", ".join(user_prefs)

    try:
        start = datetime.strptime(_get("start_date"), "%Y-%m-%d") if _get("start_date") else datetime.today()
        end = datetime.strptime(_get("end_date"), "%Y-%m-%d") if _get("end_date") else start
    except Exception:
        start = datetime.today()
        end = start
    dates = _date_range(start, end)
    num_days = max(1, len(dates))

    locs = _expand_locations(destination, suggest_locations)
    desired_docs = max(12, num_days * 8)
    desired_docs = min(desired_docs, 200)
    retriever = _retriever_for_location(vs, locs, llm, top_k=desired_docs)

    blocks = [
        f"Activities in/near {destination}" if destination else "Activities",
        f"Best things to do in {destination} for {(_get('type_of_trip') or 'travelers')}",
        f"Budget: {_get('budget','any')}; Season: {_get('season','any')}; Preferences: {prefs or 'any'}"
    ]
    if suggest_locations:
        blocks.append("Also consider: " + ", ".join(suggest_locations))
    query = " | ".join(blocks)

    docs = []
    try:
        if callable(retriever):
            docs = retriever(query) or []
        else:
            get_docs = getattr(retriever, "get_relevant_documents", None)
            if callable(get_docs):
                docs = get_docs(query) or []
            else:
                docs = getattr(retriever, "retrieve", lambda q: [])(query) or []
    except Exception as e:
        print(f"[activity_agent] Retriever failed: {e}")
        docs = []

    # # LLM fallback when index has insufficient local hits
    # try:
    #     loc_tokens = [l.lower() for l in (locs or []) if l]
    #     local_hits = 0
    #     for d in docs:
    #         txt = ((d.metadata or {}).get("source", "") + " " + (d.page_content or "")).lower()
    #         if any(tok in txt for tok in loc_tokens):
    #             local_hits += 1

    #     if local_hits < 2 and destination:
    #         gen_items = _llm_fetch_local_activities(destination, prefs, num_days=num_days, items_per_day=4, llm_model=llm)
    #         if gen_items:
    #             class _SimpleDoc:
    #                 def __init__(self, content, meta):
    #                     self.page_content = content
    #                     self.metadata = meta
    #             synth_docs = []
    #             for gi in gen_items:
    #                 content = json.dumps(gi, ensure_ascii=False)
    #                 meta = {"source": "llm_generated", "tags": [destination.lower()]}
    #                 synth_docs.append(_SimpleDoc(content, meta))
    #             docs = synth_docs + docs
    # except Exception as e:
    #     print(f"[activity_agent] LLM fallback generation failed: {e}")

    # --- stronger local evidence check + fallback generation ---
    def _count_local_hits(docs, loc_tokens):
        hits = 0
        for d in docs:
            meta = d.metadata or {}
            src = (meta.get("source") or meta.get("url") or "").lower()
            tags = [t.lower() for t in meta.get("tags", [])]
            txt = (d.page_content or "").lower()
            # strong indicators
            if any(tok in src for tok in loc_tokens):
                hits += 3
                continue
            if any(tok in tags for tok in loc_tokens):
                hits += 2
                continue
            # content token match (weaker)
            if any(tok in txt for tok in loc_tokens):
                hits += 1
        return hits

    try:
        loc_tokens = [l.lower() for l in (locs or []) if l]
        local_score = _count_local_hits(docs, loc_tokens)
        # require a stronger score for confidence; tune if needed
        # e.g., for one strong doc => 3, for two medium docs => 4, etc.
        if local_score < 3 and destination:
            # generate synthetic local items (LLM) anchored to "destination"
            gen_items = _llm_fetch_local_activities(destination, prefs, num_days=num_days, items_per_day=4, llm_model=llm)
            if gen_items:
                class _SimpleDoc:
                    def __init__(self, content, meta):
                        self.page_content = content
                        self.metadata = meta
                synth_docs = []
                for gi in gen_items:
                    # include the canonical destination token in metadata to make it match later
                    content = json.dumps(gi, ensure_ascii=False)
                    meta = {"source": f"llm_generated:{destination.lower()}", "tags": [destination.lower()]}
                    synth_docs.append(_SimpleDoc(content, meta))
                # Prepend synthetic docs so they dominate local context
                docs = synth_docs + (docs or [])
    except Exception as e:
        print(f"[activity_agent] LLM fallback generation failed: {e}")


    

    context = _format_context(docs)
    top_sources = _extract_top_sources(docs, k=3)

    try:
        trip_json = json.dumps(jsonable_encoder(inp), indent=2, ensure_ascii=False)
    except Exception:
        trip_json = json.dumps(inp if isinstance(inp, dict) else str(inp), indent=2, ensure_ascii=False)

    prompt_text = BASE_SYSTEM + "\n\n" + PROMPT_INSTRUCTIONS.format(trip=trip_json, context=context)
    if top_sources:
        prompt_text += "\n\nTop sources used (for provenance):\n" + "\n".join(top_sources)

    print(f"[activity_agent] Calling LLM with prompt (truncated)...")
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

    if not isinstance(text, str) or not text.strip():
        logger.error("[activity_agent] LLM returned empty response; using fallback suggestions. Prompt (truncated): %s", prompt_text[:600])
        day_plans = []
        for d in dates:
            user_budget = _get("budget", None)
            fd = d.strftime("%Y-%m-%d")
            suggestions = []
            primary = destination or (locs[0] if locs else "the area")

            suggestions.append({
                "time_of_day": "morning",
                "title": f"Visit {primary}",
                "why": f"{primary} offers a great morning experience and cooler temperatures.",
                "source_hints": top_sources,
                "confidence": 0.5,
                "price_level": _estimate_price_level(f"Visit {primary}", "", docs, user_budget)
            })
            suggestions.append({
                "time_of_day": "noon",
                "title": f"Local lunch and short indoor stop near {primary}",
                "why": "Rest and try local cuisine.",
                "source_hints": top_sources,
                "confidence": 0.4,
                "price_level": _estimate_price_level("Local lunch", "Try local stalls or mid-range cafes", docs, user_budget)
            })
            suggestions.append({
                "time_of_day": "evening",
                "title": f"Sunset viewpoint or market walk at {primary}",
                "why": "Golden hour and local vibes.",
                "source_hints": top_sources,
                "confidence": 0.4,
                "price_level": _estimate_price_level("Sunset viewpoint or market walk", "Local atmosphere", docs, user_budget)
            })
            suggestions.append({
                "time_of_day": "night",
                "title": "Dinner / cultural show",
                "why": "Relax and enjoy local cuisine or a brief cultural performance.",
                "source_hints": top_sources,
                "confidence": 0.4,
                "price_level": _estimate_price_level("Dinner / cultural show", "Local cuisine/culture", docs, user_budget)
            })

            try:
                location_hint = destination or (locs[0] if locs else "")
                date_obj = datetime.strptime(fd, "%Y-%m-%d")
                risk = _seasonal_risk_for_location(location_hint, date_obj)
                if risk:
                    for s in suggestions:
                        if _is_outdoor_activity(s.get("title", ""), s.get("why", "")):
                            s["weather_risk"] = True
                            s["alternatives"] = _suggest_alternatives_for_activity(s.get("title", ""))
            except Exception:
                pass

            day_plans.append({"date": fd, "suggestions": suggestions})

        return {
            "destination": destination,
            "overall_theme": f"Activities near {destination}" if destination else "Suggested activities",
            "day_plans": day_plans,
            "notes": "LLM returned empty; provided synthesized suggestions based on destination and sources.",
            "status": "fallback",
            "top_sources": top_sources
        }

    try:
        data = json.loads(text)
        data["status"] = "complete"
        if "top_sources" not in data:
            data["top_sources"] = top_sources

        # --- POST-LM VERIFICATION PASS: quick fact-check / anchoring ---
        # quick verify each suggestion is anchored to the destination tokens
        for day in data.get("day_plans", []):
            for s in day.get("suggestions", []):
                title = (s.get("title", "") or "").lower()
                # small blacklist of other known towns to detect cross-town leakage
                other_towns = ["ella", "kandy", "nuwara eliya", "hikkaduwa", "mirissa", "trincomalee"]
                if destination:
                    dest_low = destination.lower()
                else:
                    dest_low = ""
                # flag suggestions that mention a different known-town token
                for town in other_towns:
                    if town in title and town not in dest_low:
                        s.setdefault("warnings", []).append("suggestion_mentions_other_town")
                        s["confidence"] = min(s.get("confidence", 1.0), 0.5)
                        s["source_hints"] = s.get("source_hints", []) + ["potentially_nonlocal"]
                        break
                # ensure locality_confidence exists, default low if absent
                if "locality_confidence" not in s:
                    try:
                        s["locality_confidence"] = float(_compute_confidence_for_title(s.get("title", ""), docs, k=min(5, max(1, len(docs)))))
                    except Exception:
                        s["locality_confidence"] = 0.0

        try:
            heuristic_k = min(5, max(1, len(docs)))
            user_budget = _get("budget", None)
            for day in data.get("day_plans", []):
                suggestions = day.get("suggestions", [])
                date_str = day.get("date")
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d") if date_str else start
                except Exception:
                    date_obj = start
                location_hint = destination or (locs[0] if locs else "")
                try:
                    risk_for_day = _seasonal_risk_for_location(location_hint, date_obj)
                except Exception:
                    risk_for_day = False

                for s in suggestions:
                    title = s.get("title", "") or ""
                    heuristic = _compute_confidence_for_title(title, docs, k=heuristic_k)
                    confidence = max(heuristic, 0.8)
                    confidence = max(0.0, min(1.0, float(confidence)))
                    s["confidence"] = confidence
                    if "source_hints" not in s:
                        s["source_hints"] = top_sources
                    if "price_level" not in s:
                        why = s.get("why", "")
                        s["price_level"] = _estimate_price_level(title, why, docs, user_budget)

                    loc_match = _compute_confidence_for_title(title, docs, k=heuristic_k)
                    if loc_match < 0.2:
                        s["confidence"] = min(s["confidence"], 0.6)
                        s["locality_confidence"] = float(loc_match)
                    else:
                        s["locality_confidence"] = float(loc_match)

                    try:
                        if risk_for_day and _is_outdoor_activity(title, s.get("why", "")):
                            s["weather_risk"] = True
                            if "alternatives" not in s or not s["alternatives"]:
                                s["alternatives"] = _suggest_alternatives_for_activity(title)
                    except Exception:
                        pass
        except Exception as ci_e:
            print(f"[activity_agent] Confidence assignment failed: {ci_e}")

        print(f"\nDEBUG: (try block) ACTIVITY AGENT LLM RAW RESPONSE parsed successfully.")

        try:
            existing_days = { (d.get("date") or "").strip(): d for d in data.get("day_plans", []) if isinstance(d, dict) }
            final_days = []
            for d in dates:
                fd = d.strftime("%Y-%m-%d")
                day_obj = existing_days.get(fd)
                if not day_obj:
                    sample = next(iter(existing_days.values()), None)
                    if sample and sample.get("suggestions"):
                        suggestions = []
                        for s in sample["suggestions"][:4]:
                            cloned = dict(s)
                            cloned["confidence"] = min(0.9, cloned.get("confidence", 0.6) * 0.9)
                            cloned["why"] = (cloned.get("why","") + f" (planned for {fd})").strip()
                            suggestions.append(cloned)
                    else:
                        suggestions = [
                            {"time_of_day":"morning", "title": f"Explore around {destination or 'the area'}", "why":"Good morning activity.", "source_hints": top_sources, "confidence":0.5, "price_level": _estimate_price_level("", "", docs)},
                            {"time_of_day":"noon", "title": "Local lunch and short indoor stop", "why":"Rest and try local cuisine.", "source_hints": top_sources, "confidence":0.45, "price_level": _estimate_price_level("Local lunch","",docs)},
                            {"time_of_day":"evening", "title": "Sunset viewpoint or market walk", "why":"Golden hour.", "source_hints": top_sources, "confidence":0.45, "price_level": _estimate_price_level("Sunset viewpoint","",docs)},
                            {"time_of_day":"night", "title": "Dinner / cultural show", "why":"Relax and enjoy local cuisine.", "source_hints": top_sources, "confidence":0.45, "price_level": _estimate_price_level("Dinner","",docs)}
                        ]
                    day_obj = {"date": fd, "suggestions": suggestions}
                else:
                    present_tods = { s.get("time_of_day") for s in day_obj.get("suggestions", []) if isinstance(s, dict) and s.get("time_of_day") }
                    forced_slots = []
                    for tod in ("morning","noon","evening","night"):
                        if tod not in present_tods:
                            forced_slots.append({
                                "time_of_day": tod,
                                "title": f"{'Visit' if tod=='morning' else 'Enjoy'} local { 'sights' if tod=='morning' else 'food' } at {destination or 'the area'}",
                                "why": "Filled placeholder to ensure itinerary completeness.",
                                "source_hints": top_sources,
                                "confidence": 0.35,
                                "price_level": _estimate_price_level("", "", docs)
                            })
                    if forced_slots:
                        day_obj.setdefault("suggestions", []).extend(forced_slots)

                    def tod_key(s):
                        order = {"morning":0,"noon":1,"evening":2,"night":3}
                        return order.get(s.get("time_of_day"), 99)
                    day_obj["suggestions"] = sorted(day_obj.get("suggestions", []), key=tod_key)

                final_days.append(day_obj)

            data["day_plans"] = final_days
        except Exception as completeness_exc:
            print(f"[activity_agent] Day completeness enforcement failed: {completeness_exc}")

        return data

    except Exception as parse_exc:
        logger.error("[activity_agent] Could not parse LLM output as JSON: %s", parse_exc)
        logger.error("[activity_agent] Raw LLM text (truncated): %s", (text or "")[:2000])
        print(f"[activity_agent] Could not parse LLM output as JSON: {parse_exc}")
        print(f"[activity_agent] Raw LLM text (truncated): {text[:600]}")

        user_budget = _get("budget", None)
        day_plans = []
        for d in dates:
            fd = d.strftime("%Y-%m-%d")
            day_plans.append({
                "date": fd,
                "suggestions": [
                    {
                        "time_of_day": "morning",
                        "title": f"Explore around {destination or 'the area'}",
                        "why": "Nice light and cooler temps.",
                        "source_hints": [],
                        "confidence": 0.3,
                        "price_level": _estimate_price_level(f"Explore around {destination or 'the area'}", "Nice light and cooler temps.", docs, user_budget)
                    },
                    {
                        "time_of_day": "noon",
                        "title": "Local lunch & shorter indoor stop",
                        "why": "Avoid the heat.",
                        "source_hints": [],
                        "confidence": 0.3,
                        "price_level": _estimate_price_level("Local lunch & shorter indoor stop", "Avoid the heat.", docs, user_budget)
                    },
                    {
                        "time_of_day": "evening",
                        "title": "Sunset viewpoint or market walk",
                        "why": "Golden hour and local vibes.",
                        "source_hints": [],
                        "confidence": 0.3,
                        "price_level": _estimate_price_level("Sunset viewpoint or market walk", "Golden hour and local vibes.", docs, user_budget)
                    },
                    {
                        "time_of_day": "night",
                        "title": "Dinner / cultural show",
                        "why": "Relax and enjoy local cuisine/culture.",
                        "source_hints": [],
                        "confidence": 0.3,
                        "price_level": _estimate_price_level("Dinner / cultural show", "Relax and enjoy local cuisine/culture.", docs, user_budget)
                    },
                ]
            })
            try:
                location_hint = destination or (locs[0] if locs else "")
                date_obj = datetime.strptime(fd, "%Y-%m-%d")
                risk = _seasonal_risk_for_location(location_hint, date_obj)
                if risk:
                    for s in day_plans[-1]["suggestions"]:
                        if _is_outdoor_activity(s.get("title", ""), s.get("why", "")):
                            s["weather_risk"] = True
                            s["alternatives"] = _suggest_alternatives_for_activity(s.get("title", ""))
            except Exception:
                pass

        return {
            "destination": destination,
            "overall_theme": f"Activities near {destination}" if destination else "Suggested activities",
            "day_plans": day_plans,
            "notes": "LLM returned non-JSON; provided fallback suggestions.",
            "status": "fallback",
            "top_sources": top_sources
        }


# # CLI entry disabled for module import safety
# # CLI entry: build index if script run directly
# if __name__ == "__main__":
#     print("Building / refreshing FAISS index for activity retrieval...")
#     build_or_refresh_index()
#     print("Done.")