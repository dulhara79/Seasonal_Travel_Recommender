# travel_recommendation_agent.py

# Sample dataset
dataset = {
    "Kandy": [
        {"name": "Temple of the Tooth", "months": ["All"]},
        {"name": "Royal Botanical Gardens", "months": ["All"]},
        {"name": "Kandy Esala Perahera", "months": ["July", "August"]}
    ],
    "Galle": [
        {"name": "Galle Fort", "months": ["All"]},
        {"name": "Unawatuna Beach", "months": ["December", "January", "February", "March", "April"]}
    ],
    "Trincomalee": [
        {"name": "Nilaveli Beach", "months": ["May", "June", "July", "August", "September"]},
        {"name": "Koneswaram Temple", "months": ["All"]}
    ]
}

def get_valid_attractions(location, month):
    attractions = dataset.get(location, [])
    valid = [a["name"] for a in attractions if "All" in a["months"] or month in a["months"]]
    return valid

def recommend_places(user_vars):
    location = user_vars["location"]
    month = user_vars["start_date"].split("-")[1]  # extract month from YYYY-MM-DD
    valid_places = get_valid_attractions(location, month)
    return valid_places
