import json
from server.schemas.summary_schemas import SummaryAgentInputSchema
from server.agents.summary_agent.summary_agent import generate_summary

if __name__ == "__main__":
    # Example input
    # state = SummaryAgentInputSchema(
    #     destination="Meemure",
    #     start_date="2025-09-06",
    #     end_date="2025-09-10",
    #     no_of_traveler=2,
    #     budget="medium",
    #     user_preferences=["food", "culture", "adventure", "nature"],
    #     # Added nature and adventure as they are essential for Meemure
    #     type_of_trip="leisure",  # Though 'adventure' might be more accurate
    #     locations_to_visit=[
    #         "Meemure Village",
    #         "Lakegala Rock",
    #         "Knuckles Mountain Range (UNESCO World Heritage Site)",
    #         "The Paddy Fields and Local Farms",
    #         "The Traditional Chief's House (Vidane's House)"
    #     ],
    #     activities=[
    #         "Trekking and hiking through cloud forests",
    #         "Swimming in natural river pools and waterfalls",
    #         "Visiting a local family home for a traditional meal",
    #         "Learning about ancient farming techniques",
    #         "Bird watching and wildlife spotting (maybe wild elephants)",
    #         "Night walk to see the spectacular stargazing (no light pollution)"
    #     ],
    #     packing_list=[
    #         "Sturdy hiking boots & waterproof sandals",
    #         "Quick-dry clothing & warm layers (it gets cold at night)",
    #         "Raincoat or poncho (weather is unpredictable)",
    #         "Torch or headlamp (essential for night)",
    #         "Reusable water bottle & water purification tablets",
    #         "Power bank (electricity is limited/solar-powered)",
    #         "Basic first-aid kit",
    #         "Cash (LKR) - No ATMs or card facilities for miles"
    #     ],
    #     additional_info="Meemure is extremely remote with no modern infrastructure. Transport is by 4x4 jeep or foot. Accommodation is in very basic homestays. This is a trip for cultural immersion and nature, not luxury. Be prepared to disconnect and respect local traditions. The journey from Kandy is a 3-4 hour rough jeep ride."
    # )

    state = SummaryAgentInputSchema(
            destination= "Jaffna",
            season= "Dry Season",
            start_date= "2025-09-10",
            end_date= "2025-09-14",
            no_of_traveler= 5,
            budget= "medium",
            user_preferences= [],
            type_of_trip= "leisure",
            locations_to_visit= [],
            activities= [],
            packing_list= [],
            additional_info= None,
            status= "complete",
            messages= []
    )

    result = generate_summary(state)

    print("=== Ressult from Summary Agent ===\n")
    print(result)

    # Print the refined summary
    print("\n=== Final Trip Summary ===\n")
    print(result.summary)

    # Or debug the full structured object
    print("\n=== Full Result Object ===\n")
    print(json.dumps(result.model_dump(), indent=2))
