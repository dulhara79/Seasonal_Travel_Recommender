# from server.agents.followup_agent.followup_agent import create_followup_questions
#
# if __name__ == "__main__":
#     # Example current state with some known information
#     current_state = {
#         "destination": "Gampaha",
#         "start_date": "",
#         "end_date": "",
#         "no_of_traveler": "2",
#         "type_of_trip": "adventure",
#         "budget": "medium",
#         "travel_with": "partner",
#         "interests": "landscape photography, hiking, culture, wildlife, beaches",
#         "additional_info": "",
#     }
#
#     # List of missing mandatory fields
#     missing_fields = ["start_date", "end_date"]
#
#     # Generate follow-up questions for the missing fields
#     questions = create_followup_questions(current_state, missing_fields)
#
#     print("Generated Follow-Up Questions:")
#     for field, question in questions.items():
#         print(f"{field}: {question}")

# python
import unittest
from server.agents.followup_agent.followup_agent import FollowUpAgent

class TestFollowUpAgent(unittest.TestCase):
    def setUp(self):
        self.mandatory_fields = ["destination", "start_date", "end_date", "no_of_traveler", "type_of_trip"]
        self.question_templates = {
            "destination": "🌍 Where would you like to travel?",
            "start_date": "📅 What is your trip start date? (YYYY-MM-DD)?",
            "end_date": "📅 What is your trip end date? (YYYY-MM-DD)?",
            "no_of_traveler": "👥 How many people are traveling?",
            "type_of_trip": "🎯 What type of trip is this (leisure, adventure, business, family)?"
        }
        self.agent = FollowUpAgent(
            question_templates=self.question_templates,
            mandatory_fields=self.mandatory_fields
        )

    def test_collect_missing_fields(self):
        # Simulate a state with some missing fields
        followup_answers = {
            "destination": "Paris",
            "start_date": None,
            "end_date": None,
            "no_of_traveler": 2,
            "type_of_trip": ""
        }
        additional_info = "Planning a trip to Paris with 2 people."

        fields, missing_questions = self.agent.collect(
            additional_info=additional_info,
            followup_answers=followup_answers
        )

        # Verify filled fields
        self.assertEqual(fields["destination"], "Paris")
        self.assertEqual(fields["no_of_traveler"], 2)

        # Verify missing questions
        self.assertIn("start_date", missing_questions)
        self.assertIn("end_date", missing_questions)
        self.assertIn("type_of_trip", missing_questions)
        self.assertEqual(missing_questions["start_date"], "📅 What is your trip start date? (YYYY-MM-DD)?")
        self.assertEqual(missing_questions["end_date"], "📅 What is your trip end date? (YYYY-MM-DD)?")
        self.assertEqual(missing_questions["type_of_trip"], "🎯 What type of trip is this (leisure, adventure, business, family)?")

    def test_collect_all_fields_provided(self):
        # Simulate a state where all fields are provided
        followup_answers = {
            "destination": "Paris",
            "start_date": "2025-09-01",
            "end_date": "2025-09-10",
            "no_of_traveler": 2,
            "type_of_trip": "leisure"
        }
        additional_info = "Planning a trip to Paris with 2 people."

        fields, missing_questions = self.agent.collect(
            additional_info=additional_info,
            followup_answers=followup_answers
        )

        # Verify no missing fields
        self.assertEqual(fields["destination"], "Paris")
        self.assertEqual(fields["start_date"], "2025-09-01")
        self.assertEqual(fields["end_date"], "2025-09-10")
        self.assertEqual(fields["no_of_traveler"], 2)
        self.assertEqual(fields["type_of_trip"], "leisure")
        self.assertEqual(len(missing_questions), 0)

if __name__ == "__main__":
    unittest.main()