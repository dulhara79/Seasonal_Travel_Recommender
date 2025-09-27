from server.schemas.summary_schemas import SummaryAgentInputSchema

payload = {
    'summary': 'Packing list for a family trip to Kandy during the Dry Season',
    'duration_days': 6,
    'categories': [{'name': 'Essentials', 'items': [{'name': 'Lightweight clothing', 'reason': 'Comfort in warm weather'}, {'name': 'Sunscreen SPF 30+', 'reason': 'Protection from strong sun'}, {'name': 'Insect repellent', 'reason': 'Prevention against insect bites'}, {'name': 'Comfortable walking shoes', 'reason': 'For exploring the attractions'}]}, {'name': 'Weather-specific', 'items': [{'name': 'Umbrella', 'reason': 'Possible brief showers during the dry season'}]}, {'name': 'Activity-specific', 'items': [{'name': 'Camera', 'reason': 'Capture memories of the scenic views'}, {'name': 'Picnic blanket', 'reason': 'Enjoy outdoor meals or relax in parks'}]}, {'name': 'Documents & Safety', 'items': [{'name': 'Travel insurance documents', 'reason': 'Emergency coverage'}, {'name': 'First aid kit', 'reason': 'Basic medical needs'}]}, {'name': 'Optional nice-to-have', 'items': [{'name': 'Portable charger', 'reason': 'Keep devices charged for photos and navigation'}, {'name': 'Travel journal', 'reason': 'Record memorable moments'}]}],
    'notes': ['Add modest white attire for temple visits if applicable', 'Keep liquids under airline limits', 'Pack a reusable water bottle for staying hydrated during outings']
}

s = SummaryAgentInputSchema(destination='Kandy', start_date='2025-09-01', end_date='2025-09-06', no_of_traveler=4, type_of_trip='family', packing_list=payload)
print('Created SummaryAgentInputSchema successfully')
print(type(s.packing_list))
print(s.packing_list)
