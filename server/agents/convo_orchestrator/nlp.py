# import spacy
# from typing import Optional
# from .utils import normalize_dates
# from .schemas import Slots
#
# _nlp = spacy.load("en_core_web_sm")
#
# def extract_slots(user_text: str) -> Slots:
#     '''
#     Extract destination (GPE/LOC), preference (noun chunks/adjectives), and date range using dateparser.
#     '''
#     doc = _nlp(user_text)
#
#     destination = None
#
#     # prefer longest GPE/LOC span
#     locs = [ent for ent in doc.ents if ent.lable_ in ('GPE', 'LOC', 'FAC')]
#     if locs:
#         destinatiopn = max(locs, key=lambda e: len(e.text)).text
#
#     # date
#     start_date, end_date = normalize_dates(user_text)
#
#     # preference
#     preferences = None
#     lowered = user_text.lower()
#     for key in ("i like", "i prefer", "i’m into", "im into", "looking for", "interested in"):
#         idx = lowered.find(key)
#         if idx != -1:
#             tail = user_text[idx + len(key):].strip('.:')
#             # take short tail
#             preferences = tail.split(".")[0][:120].strip()
#             break
#
#     # fallback: use frequent nouns if no explicit clue
#     if not preferences:
#         nouns = [t.text for t in doc if t.pos_ in ("NOUN", "PROPN") and t.is_alpha]
#         if nouns:
#             preferences = ' '.join(nouns[:6])
#
#     return Slots(
#         destination=destination,
#         start_date=start_date,
#         end_date=end_date,
#         preferences=preferences
#     )
#
# def missing_slots(slots: Slots):
#     missing = []
#
#     if not slots.destination:
#         missing.append('destination')
#     if not slots.start_date or not slots.end_date:
#         missing.append('date')
#     if not slots.preferences:
#         missing.append('preferences')
#
#     return missing
#
# def build_clarifying_question(slots: Slots) -> Optional[str]:
#     miss = missing_slots(slots)
#
#     if not miss:
#         return None
#
#     prompts = []
#     if 'destination' in miss:
#         prompts.append('Where are you traveling to?')
#     if 'dates' in miss:
#         prompts.append('When are you planning to travel?')
#     if 'preferences' in miss:
#         prompts.append('What kind of activities do you enjoy (e.g., cultural, adventure, relaxing)?')
#
#     return ' '.join(prompts)

# convo_orchestrator/nlp.py
import spacy
from dateparser.search import search_dates
from typing import Optional, Tuple
import re
from .schemas import SlotOutput

# load spaCy model (ensure installed)
nlp = spacy.load("en_core_web_sm")

DATE_PREP_REGEX = re.compile(r'(\bfrom\b.*\bto\b|\bfrom\b.*\b-\b|\b\d{1,2}\s?[A-Za-z]+\b.*\d{4})', re.I)

def extract_location(text: str) -> Optional[str]:
    doc = nlp(text)
    # prefer GPE, LOC, or ORG entities as destination
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
            return ent.text
    # fallback: attempt to find pattern "to <Place>" or "going to <Place>"
    m = re.search(r'\bto\s+([A-Z][\w\s,.-]+)', text)
    if m:
        # strip trailing 'from' or dates
        place = m.group(1).strip()
        # remove trailing dates
        place = re.split(r'\bfrom\b|\bon\b|\bfrom\b', place, flags=re.I)[0].strip()
        return place
    return None

def extract_dates(text: str) -> Tuple[Optional[str], Optional[str]]:
    # Try search_dates to detect start/end or ranges
    results = search_dates(text, languages=['en'])
    if not results:
        return None, None
    # naive: take first and last recognised dates
    dates = [r[1].date().isoformat() for r in results]
    if len(dates) == 1:
        return dates[0], dates[0]
    return dates[0], dates[-1]

def extract_preferences(text: str) -> Optional[str]:
    doc = nlp(text.lower())
    # common preference tags
    prefs = []
    for token in doc:
        if token.lemma_ in ("culture", "cultural", "adventure", "relax", "beach", "hike", "food", "nature", "family"):
            prefs.append(token.lemma_)
    if prefs:
        return ", ".join(sorted(set(prefs)))
    # fallback: try noun chunks after "like" or "prefer"
    m = re.search(r'\b(i like|i prefer|i want|i enjoy)\s+([^.]+)', text, re.I)
    if m:
        return m.group(2).strip().rstrip('.')
    return None

def parse_user_text(text: str) -> SlotOutput:
    destination = extract_location(text)
    start_date, end_date = extract_dates(text)
    preferences = extract_preferences(text)

    # Normalise "Sri Lanka" if part of dest but missing capitals
    return SlotOutput(destination=destination, start_date=start_date, end_date=end_date, preferences=preferences)
