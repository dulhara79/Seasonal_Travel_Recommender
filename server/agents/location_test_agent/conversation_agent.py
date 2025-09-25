# conversation_agent.py

def get_user_inputs():
    print("Hello! 👋 I can recommend travel destinations in Sri Lanka.")
    location = input("📍 Enter the location you want to visit: ")
    start_date = input("🗓️ Enter the start date (YYYY-MM-DD): ")
    end_date = input("🗓️ Enter the end date (YYYY-MM-DD): ")
    return {
        "location": location,
        "start_date": start_date,
        "end_date": end_date
    }
