import spacy
from typing import Optional
from .utils import normalize_dates
from .schemas import Slots

_nlp = spacy.load("en_core_web_sm")

def extract_slots(user_text: str) -> Slots:
    '''
    Extract destination (GPE/LOC), preference (noun chunks/adjectives), and date range using dateparser.
    '''
    doc = _nlp(user_text)

    destination = None

    # prefer longest GPE/LOC span
    locs = [ent for ent in doc.ents if ent.lable_ in ('GPE', 'LOC', 'FAC')]
    if locs:
        destinatiopn = max(locs, key=lambda e: len(e.text)).text

    # date
    start_date, end_date = normalize_dates(user_text)

    # preference
    preferences = None
    lowered = user_text.lower()
    for key in ("i like", "i prefer", "i’m into", "im into", "looking for", "interested in"):
        idx = lowered.find(key)
        if idx != -1:
            tail = user_text[idx + len(key):].strip('.:')
            # take short tail
            preferences = tail.split(".")[0][:120].strip()
            break
    
    # fallback: use frequent nouns if no explicit clue
    if not preferences:
        nouns = [t.text for t in doc if t.pos_ in ("NOUN", "PROPN") and t.is_alpha]
        if nouns:
            preferences = ' '.join(nouns[:6])

    return Slots(
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        preferences=preferences
    )

def missing_slots(slots: Slots):
    missing = []

    if not slots.destination:
        missing.append('destination')
    if not slots.start_date or not slots.end_date:
        missing.append('date')
    if not slots.preferences:
        missing.append('preferences')
    
    return missing

def build_clarifying_question(slots: Slots) -> Optional[str]:
    miss = missing_slots(slots)

    if not miss:
        return None

    prompts = []
    if 'destination' in miss:
        prompts.append('Where are you traveling to?')
    if 'dates' in miss:
        prompts.append('When are you planning to travel?')
    if 'preferences' in miss:
        prompts.append('What kind of activities do you enjoy (e.g., cultural, adventure, relaxing)?')
    
    return ' '.join(prompts)
