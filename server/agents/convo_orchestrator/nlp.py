# nlp.py
import re
from typing import Optional
from schemas import Slots
from utils import normalize_dates

# try to import & load spaCy model; if not available, we'll fallback to gazetteer
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None

# small built-in gazetteer for Sri Lanka / common travel places — extend as needed
_GAZETTEER = {
    "meemure", "kandy", "ella", "nuwara eliya", "sigiriya", "galle", "trincomalee", "mithirigala",
    "anuradhapura", "polonnaruwa", "hatton", "haputale"
}

def _gazetteer_lookup(text: str) -> Optional[str]:
    lowered = text.lower()
    # longest match
    matches = [g for g in _GAZETTEER if g in lowered]
    if matches:
        return max(matches, key=len).title()
    # try simple "to <place>" pattern
    m = re.search(r"\bto\s+([A-Za-z\s']{2,40})\b", text, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        # if multi-word candidate contains stopwords or verbs, ignore
        return candidate.title()
    return None

def extract_slots(user_text: str) -> Slots:
    """
    Extract destination (GPE/LOC), preferences, and date range.
    Returns a Schemas.Slots pydantic model instance.
    """
    destination = None
    preferences = None

    # Try spaCy NER if available
    if _nlp:
        doc = _nlp(user_text)
        # prefer the longest entity labeled GPE/LOC/FAC
        locs = [ent for ent in doc.ents if ent.label_ in ("GPE", "LOC", "FAC")]
        if locs:
            destination = max(locs, key=lambda e: len(e.text)).text

        # fallback preferences: look for pattern "i like", "i prefer", etc.
        lowered = user_text.lower()
        for key in ("i like", "i prefer", "i’m into", "im into", "looking for", "interested in", "i want"):
            idx = lowered.find(key)
            if idx != -1:
                tail = user_text[idx + len(key):].strip('.: ')
                preferences = tail.split(".")[0][:120].strip()
                break

        # fallback: try noun/proper nouns
        if not preferences:
            nouns = [t.text for t in doc if t.pos_ in ("NOUN", "PROPN") and t.is_alpha]
            if nouns:
                preferences = " ".join(nouns[:6])
    else:
        # no NLP model — use simple heuristics
        lowered = user_text.lower()
        for key in ("i like", "i prefer", "i'm into", "im into", "looking for", "interested in", "i want"):
            idx = lowered.find(key)
            if idx != -1:
                tail = user_text[idx + len(key):].strip('.: ')
                preferences = tail.split(".")[0][:120].strip()
                break
        if not preferences:
            # collect 1-3 capitalized words as preference (best-effort)
            prefs = re.findall(r"\b([A-Z][a-z]{1,20})\b", user_text)
            if prefs:
                preferences = " ".join(prefs[:3])

    # dates
    start_date, end_date = normalize_dates(user_text)

    # destination: spaCy didn't find -> gazetteer
    if not destination:
        dest = _gazetteer_lookup(user_text)
        if dest:
            destination = dest

    # final normalization
    if destination:
        destination = destination.strip()

    return Slots(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        preferences=preferences
    )

def missing_slots(slots: Slots):
    """
    Return list of missing slot keys: 'destination', 'date', 'preferences'
    Note: 'date' means start/end not both present.
    """
    missing = []
    if not slots.destination:
        missing.append("destination")
    # require at least a start date (if only one present we'll treat as single-day)
    if not slots.start_date or not slots.end_date:
        missing.append("date")
    if not slots.preferences:
        missing.append("preferences")
    return missing

def build_clarifying_question(slots: Slots) -> Optional[str]:
    miss = missing_slots(slots)
    if not miss:
        return None

    prompts = []
    if "destination" in miss:
        prompts.append("Where are you traveling to?")
    if "date" in miss:
        prompts.append("When are you planning to travel? (dates or approximate range)")
    if "preferences" in miss:
        prompts.append("What kind of activities do you enjoy (e.g., cultural, adventure, relaxing)?")
    return " ".join(prompts)
