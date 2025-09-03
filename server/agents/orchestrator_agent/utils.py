# utils.py
from datetime import datetime
from typing import Optional, Tuple, List
import dateparser
import spacy

nlp = spacy.load("en_core_web_sm")

def normalize_dates(free_text: str) -> Tuple[Optional[str], Optional[str]]:
    text = free_text.replace("–", "-").replace("—", "-")
    try:
        dates = dateparser.search.search_dates(text, settings={"PREFER_DATES_FROM": "future"})
    except Exception:
        dates = None
    if not dates:
        return None, None
    uniq = []
    for _, dt in dates:
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if not uniq or dt.date() != uniq[-1].date():
            uniq.append(dt)
        if len(uniq) == 2:
            break
    if len(uniq) == 1:
        s = uniq[0].date().isoformat()
        return s, s
    if len(uniq) >= 2:
        s = min(uniq[0], uniq[1]).date().isoformat()
        e = max(uniq[0], uniq[1]).date().isoformat()
        return s, e
    return None, None

def iso_or_none(dt) -> Optional[str]:
    try:
        return datetime.fromisoformat(dt).date().isoformat()
    except Exception:
        return None

def pretty_date(iso: Optional[str]) -> Optional[str]:
    if not iso:
        return None
    return datetime.fromisoformat(iso).strftime("%b %d, %Y")

def join_nonempty(parts: List[Optional[str]]) -> str:
    return ", ".join([p for p in parts if p])

def extract_entities(text: str) -> List[str]:
    doc = nlp(text)
    return [ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC", "ORG")]
