from typing import List, Dict, Any, Tuple


WEATHER_RULES = {
    "summer": [
        ("Sunscreen SPF 30+", "High UV in summer"),
        ("Hat/Cap", "Protects from sun"),
        ("Light cotton clothes", "Breathable in heat")
    ],
    "monsoon": [
        ("Umbrella/Raincoat", "Frequent showers"),
        ("Quick-dry shoes", "Wet conditions"),
    ],
    "winter": [
        ("Warm jacket", "Low night temperatures"),
        ("Scarf/Gloves", "Wind chill protection"),
    ]
}
ACTIVITY_RULES = {
    "hiking": [
        ("Hiking shoes", "Grip on trails"),
        ("Water bottle (1L)", "Hydration during activity"),
        ("Small first-aid kit", "Minor injuries on trails"),
    ],
    "temple": [
        ("Modest attire", "Dress code for sacred sites"),
        ("Light shawl/sarong", "Cover shoulders at entrances"),
    ],
    "beach": [
        ("Swimwear", "Water activities"),
        ("Microfiber towel", "Quick drying"),
    ],
}

DOC_SAFETY = [
    ("ID/Passport", "ID verification at check-ins"),
    ("Basic meds", "Headache/cold relief"),
]

LOW_COST_PRIORITY = ["water bottle", "umbrella", "hat", "shawl", "towel", "light", "scarf", "raincoat"]

def normalize(s: str) -> str:
    return (s or "").strip().lower()

def infer_activity_tags(activities: List[str]) -> List[str]:
    tags = []
    for a in activities or []:
        a_l = normalize(a)
        if "hiking" in a_l or "trail" in a_l:
            tags.append("hiking")
        if "temple" in a_l or "religious" in a_l or "shrine" in a_l or "monastery" in a_l:
            tags.append("temple")
        if "beach" in a_l or "coast" in a_l or "swim" in a_l:
            tags.append("beach")
    return list(dict.fromkeys(tags))  # de-dup preserving order

def seed_categories() -> List[Dict[str, Any]]:
    return [
        {"name": "Essentials", "items": []},
        {"name": "Weather-specific", "items": []},
        {"name": "Activity-specific", "items": []},
        {"name": "Documents & Safety", "items": []},
        {"name": "Optional nice-to-have", "items": []},
    ]

def push_items(cat: Dict[str, Any], pairs: List[Tuple[str, str]]):
    for name, reason in pairs:
        # de-dup inside category
        if not any(normalize(x["name"]) == normalize(name) for x in cat["items"]):
            cat["items"].append({"name": name, "reason": reason})

def rule_based_pack(season: str, activities: List[str]) -> Dict[str, Any]:
    cats = seed_categories()

    # Essentials: always present
    push_items(cats[0], [
        ("Toothbrush & toiletries", "Daily hygiene"),
        ("Phone charger & power bank", "Battery for maps/photos")
    ])

    # Weather
    s = normalize(season)
    if s in WEATHER_RULES:
        push_items(cats[1], WEATHER_RULES[s])

    # Activities
    for tag in infer_activity_tags(activities):
        push_items(cats[2], ACTIVITY_RULES.get(tag, []))

    # Documents & Safety
    push_items(cats[3], DOC_SAFETY)

    # Optional (cheap comfort items first)
    push_items(cats[4], [("Travel pillow", "Comfort on buses")])

    return {
        "summary": "Packing list tailored to season and planned activities.",
        "duration_days": None,
        "categories": cats,
        "notes": [
            "Prioritize essentials; add items based on final itinerary.",
            "Check airline liquid limits and baggage policy."
        ]
    }

def fairness_sort(categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def is_low_cost(item_name: str) -> bool:
        name = normalize(item_name)
        return any(cue in name for cue in LOW_COST_PRIORITY)
    out = []
    for cat in categories:
        essentials, optional = [], []
        for it in cat["items"]:
            (essentials if is_low_cost(it["name"]) else optional).append(it)
        out.append({"name": cat["name"], "items": essentials + optional})
    return out
