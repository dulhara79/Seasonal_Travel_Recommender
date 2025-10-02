# Seasonal Travel Recommender

Developer README — accurate snapshot of the codebase and how to run and interact with it.

This project is a multi-agent travel planning assistant focused on Sri Lanka. It uses a FastAPI backend to orchestrate several agents (orchestrator, location, activity, packing, summary) and a React/Vite frontend.

## Repo layout (important files)

- server/: FastAPI backend and agent implementations.
  - server/api/main.py — FastAPI app entrypoint.
  - server/api/route.py — Main planning endpoint: `POST /api/query`.
  - server/api/conversations.py — Conversation CRUD endpoints: create, append, list, get, delete, update title.
  - server/utils/ — DB and config helpers (chat_history.py, config.py, db.py).
  - server/agents/ — Individual agent implementations (orchestrator_agent, summary_agent, location_agent, activity_agent, packing_agent, etc.).
  - server/workflow/ — LangGraph workflow definition and agent nodes (`workflow.py`, `agent_nodes.py`).
  - server/schemas/ — Pydantic schemas used by agents and API.

- client/: React + Vite frontend.
  - client/src/contexts/AuthContext.jsx — API wrappers and auth.
  - client/src/components/ChatInterface.jsx — Main chat UI and integration with `/api/query` and conversations API.

- data/: Bundled vector stores and FAISS/Chroma indexes used by agents.

## Quick start (developer)

Prerequisites:
- Python 3.11+ (recommended)
- Node.js 18+ (for client)
- MongoDB instance (local or remote)

1. Backend (PowerShell commands)

# from repo root
cd server; python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Copy environment variables
copy ..\.env.example .\.env
# Edit server/.env and fill your keys (OpenAI, MongoDB)

# Run the API (dev)
uvicorn server.api.main:app --reload --port 8000

2. Frontend (PowerShell)

cd client
npm install
npm run dev
# Open http://localhost:5173

## Environment variables
See `.env.example` for the full list. Key ones:
- MONGODB_URI, MONGODB_DB — MongoDB connection
- OPENAI_API_KEY, OPENAI_MODEL — LLM access
- GEMINI_API_KEY, GEMINI_MODEL — optional
- JWT_SECRET — for auth
- ALLOWED_ORIGINS — CORS settings

## API reference

1. POST /api/query
- Purpose: Run the planning workflow for a user query. The workflow is resumable and non-blocking for the orchestrator.
- Request JSON shape:
  {
    "query": "I want to plan a trip to Matara for 4 people in October",
    "previous_state": null // or the last `current_state` returned by the API
  }
- Response JSON shape:
  {
    "response": "<final_response text or follow-up question>",
    "current_state": { ... }  // Full state object; contains structured fields and metadata
  }

Important keys in `current_state`:
- trip_data: Orchestrator output (may be a Pydantic-like dict); fields include: destination, start_date, end_date, no_of_traveler, user_preferences, type_of_trip, status, messages
- location_recs / location_recommendations: structured location agent output
- activity_recs / activity_recommendations: activity planner output (may include `day_plans`)
- packing_recs / packing_list: packing agent output
- latest_summary: last generated summary (markdown)
- final_response: the message text to show the user
- _processing_steps: a list of lightweight step records: { node, timestamp, note }
- _processing_last_node: the last node name that executed (string)

Notes:
- Orchestrator non-blocking behavior: if the orchestrator needs more information, the API returns `trip_data.status == 'awaiting_user_input'` and `trip_data.messages` will contain a follow-up question(s). The frontend should display the question to the user and then call `/api/query` again with `query` set to the user's answer and `previous_state` set to the last `current_state` returned — the router will route the reply back to the orchestrator which resumes the loop.

2. Conversations endpoints (server/api/conversations.py)
- POST /api/conversations/ — Create a conversation. Payload: { session_id?: str, title?: str }
- POST /api/conversations/append — Append a message. Payload shape:
  {
    "conversation_id": "<id>",
    "message": {
      "role": "user|agent|system",
      "text": "...",
      "metadata": { ... },
      "timestamp": "2025-10-01T12:34:56Z"
    }
  }
  The client (`AuthContext.appendChatMessage`) already constructs this shape.
- GET /api/conversations/list — List user's conversations
- GET /api/conversations/{id} — Get a single conversation
- DELETE /api/conversations/{id} — Delete
- PATCH /api/conversations/{id}/title — Update title: payload { "title": "New title" }

## Orchestrator behavior & resume flow
- The orchestrator agent extracts structured trip data using an LLM. Mandatory fields are: destination, start_date, end_date, no_of_traveler, type_of_trip, user_preferences.
- If any mandatory field is missing, the orchestrator returns immediately with status `awaiting_user_input` and a `messages` array containing a follow-up question: { type: 'followup', field: '<field>', question: '<text>' }
- The frontend should present the question to the user and then re-call `/api/query` with `previous_state` set to the last `current_state` and `query` equal to the user's reply.
- The backend router detects when `trip_data.status == 'awaiting_user_input'` and routes the incoming reply to the orchestrator node so the agent will resume using the `user_responses` parameter.

## Frontend notes
- `client/src/contexts/AuthContext.jsx` contains API wrappers; `appendChatMessage` now sends a message object with a timestamp and metadata.
- `client/src/components/ChatInterface.jsx` receives the `current_state` from `/api/query` and shows a small processing area with the last executing node and a collapsible processing steps timeline using `_processing_last_node` and `_processing_steps`.
- The frontend derives a friendly conversation title from the first user query and PATCHes it to `/api/conversations/{id}/title` if the server-side title remains default.

## Agents overview
- orchestrator_agent: Extracts structured trip data, produces follow-up questions, validates dates, infers Sri Lanka seasons.
- location_agent: Recommends destinations (returns `location_recs`).
- activity_agent: Produces `activity_recommendations` with `day_plans` (each day contains `suggestions` with title, why, time_of_day, price_level, confidence).
- packing_agent: Produces `packing_recs` / `packing_list` with categories and notes.
- summary_agent: Consumes the structured outputs and returns a Markdown summary; robust to key-name variants (activity_recs vs activity_recommendations).

## Development notes & tips
- Workflow engine: `server/workflow/workflow.py` builds a StateGraph with nodes defined in `agent_nodes.py` — changes there affect routing and conditional logic.
- To test resumable orchestrator flows manually:
  1. POST /api/query with { "query": "I want to plan a trip to Sri Lanka for 4" }
  2. If response.trip_data.status == 'awaiting_user_input', read trip_data.messages[0].question and show to user.
  3. POST /api/query again with query set to the user's answer and previous_state set to the last returned `current_state`.

## Troubleshooting
- 422 on `/api/conversations/append`: Ensure your payload matches the expected nested `message` shape. The client context's `appendChatMessage` helper constructs the correct payload.
- If the workflow fails to initialize, check the startup logs. Missing env vars (OpenAI key, Mongo URI) are common.

## Next improvements (ideas)
- Add SSE or WebSocket streaming for per-node progress updates to the frontend.
- Add unit tests for `summary_agent` to validate packing/activity formatting.
- Provide a sample dataset for local development (small FAISS/Chroma) and deterministic mocks for the LLM calls.


## License
MIT
