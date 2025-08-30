# Seasonal Travel Recommender 🏖️

> Seasonal Travel Recommender - Weather Data Agent, Activity Suggestor, Packing List Generator

Seasonal Travel Recommender is a small multi-agent AI system that helps travellers plan short trips based on season and weather. Given a free-text user query (destination, dates, preferences), the system checks the weather for the travel dates, suggests suitable activities, and generates a practical packing list.

## Vision
Make trip planning quick and practical by combining weather-aware recommendations with activity suggestions and a concise packing checklist. The system is designed for demonstrations, coursework, and as a starting point for a lightweight web or CLI travel assistant.

## Core features
- Parse free-text user requests (destination, dates, preferences).
- Query free weather APIs for the destination and date range.
- Suggest activities matched to weather, season and user preferences.
- Generate a packing list derived from forecast and selected activities.
- Produce a final, conversational recommendation combining all agents' outputs.

## Agents (components)

1. Conversation Agent (NLP + Orchestration)
	 - Input: raw user message.
	 - Responsibilities: extract destination, dates and preferences; call other agents; format final natural-language reply.

2. Weather Data Agent
	 - Input: destination + dates.
	 - Responsibilities: resolve location to coordinates (when needed), call a free weather API (e.g. Open-Meteo), return structured forecast (daily temps, precipitation, conditions).

3. Activity Suggester
	 - Input: forecast + user preferences.
	 - Responsibilities: map weather → suitable activities (rule-based + small location-specific dataset). Provide alternatives and short explanations.

4. Packing List Generator
	 - Input: forecast + chosen activities.
	 - Responsibilities: produce a concise packing checklist (clothing, rain/sun protection, activity-specific gear).

5. Aggregator / Orchestrator (part of Conversation Agent)
	 - Input: JSON outputs from other agents.
	 - Responsibilities: combine results and produce a friendly, explainable response for the user.

## Example
User: "I'm going to Kandy, Sri Lanka from 2024-12-15 to 2024-12-20. I like cultural activities."

Minimal structured outputs (examples):

Weather Data Agent →
```
{
	"avg_temp": "26°C",
	"conditions": [
		{"date":"2024-12-15","status":"Sunny"},
		{"date":"2024-12-16","status":"Cloudy"},
		{"date":"2024-12-17","status":"Rainy"}
	]
}
```

Activity Suggester →
```
{
	"activities": [
		{"day":"2024-12-15","activity":"Visit Temple of the Tooth"},
		{"day":"2024-12-16","activity":"Royal Botanical Gardens"},
		{"day":"2024-12-17","activity":"Indoor tea tasting tour"}
	]
}
```

Packing List Generator →
```
{
	"packing_list":["Light cotton clothes","Umbrella","Walking shoes","Sunscreen","Modest attire for temples"]
}
```

Final response (Aggregator): short human-friendly paragraph summarising weather, suggested activities, and packing.

## Conversation flow (user journey)
- Greeting / Clarify intent
- Ask or extract missing details (dates, duration, preferences)
- Call Weather Agent and present a concise weather summary
- Suggest activities (ask for acceptance or alternatives)
- If accepted, produce packing list and closing message

The system is designed to behave like a helpful travel assistant: ask clarifying questions, explain why recommendations were made (explainability), and offer alternatives.

## Team split (suggested)
- Conversation & Orchestration: NLP, LLM prompts, final formatting.
- Weather & IR: location resolution, API integration and data parsing.
- Activity Suggester: rules, location/activity dataset, fairness checks.
- Packing & Security: packing rules, basic authentication and API key management, commercialization notes.

## Security & privacy notes
- Keep API keys out of source control (use environment variables or secret manager).
- Sanitize user input before any external query to avoid injection attacks.
- Avoid logging sensitive user data; if storing any personal data, follow minimal retention and secure storage.

## Responsible AI
- Explainability: accompany suggestions with short reasons (e.g. "suggested because forecast shows sunny weather").
- Fairness: include low-cost and no-cost options among activity suggestions.
- Privacy: don't share user locations or dates publicly.

## Commercialization ideas
- Free tier: weather + 3 activity suggestions + basic packing list.
- Premium tier: multi-day itineraries, live updates, offline packing checklist, richer personalization.

## Next steps (implementation)
1. Create a small Conversation Agent skeleton (CLI or minimal web UI).
2. Implement Weather Data Agent using Open-Meteo (free) and add location-to-coordinates lookup.
3. Build a small activity dataset and a rule-based suggester.
4. Implement Packing List Generator and wire everything through the Conversation Agent.

If you'd like, I can now add the Conversation Agent skeleton (Python CLI) and a Weather Agent example using Open-Meteo so you have a runnable prototype.

---
## Contributors:
- [Dulhara Kaushalya](https://github.com/dulhara79)  
- [Senuvi Layathma](https://github.com/SENUVI20)
- [Dewdu Sendanayake](https://github.com/DewduSendanayake)
- [Uvindu Seneviratne](https://github.com/UVINDUSEN)

---
##  License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
