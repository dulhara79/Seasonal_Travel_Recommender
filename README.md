# Seasonal Travel Recommender

A lightweight multi-agent travel assistant that helps plan short trips by extracting trip details from user input, suggesting activities, checking likely weather, producing a packing list, and generating a friendly trip summary.

This repository contains a FastAPI backend (agents and workflow) and a small React + Vite frontend.

Contents
- `client/` — React (Vite) frontend that provides a Conversation UI and Summary view.
- `server/` — FastAPI backend with agents, workflow graph, APIs, and schemas.
- `data/` — Prebuilt vector stores and databases used by agents (FAISS, Chroma).

Quick overview
- Purpose: Given a free-text user request (destination, dates, preferences), extract structured trip details, reason about weather and seasonal suitability, suggest activities, and produce a packing list and a human-friendly summary.
- Intended audience: demo projects, coursework, and as a starting point for building advanced travel assistants.

Architecture
- Frontend: React + Vite app in `client/`.
- Backend: FastAPI app in `server/` exposing REST endpoints and orchestrating a workflow of modular agents.
- Agents: Python modules implementing responsibilities such as extraction (orchestrator), activity suggestion (RAG + LLM fallback), packing generator, and summary generation.

Key files and modules
- `server/api/main.py` — FastAPI application, CORS config, and app entry points.
- `server/api/route.py` — API routes (e.g., `/api/chat`) that run the orchestrator/workflow.
- `server/workflow/graph_builder.py` — Builds the workflow/state graph that connects agents.
- `server/agents/` — Folder containing agent implementations (orchestrator, activity agent, summary agent, packing agent, etc.).

Requirements
- Python 3.10+ recommended. See `server/requirements.txt` for details (FastAPI, Uvicorn, LangChain and related packages, HTTPX, spaCy, etc.).
- Node.js + npm (or Yarn) for the frontend (see `client/package.json`).

Quick start — server (development)
1. Create and activate a Python virtual environment and install dependencies:

```powershell
cd server
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Configure environment variables required by LLM providers and other services (do NOT commit secrets). Common variables used by the codebase include `OPENAI_API_KEY` and `OPENAI_MODEL` — check `server/utils/config.py` for the exact names and defaults.

```powershell
$env:OPENAI_API_KEY = "sk-..."
$env:OPENAI_MODEL = "gpt-4o-mini"
```

3. (Optional) Pre-build or let the activity agent build its FAISS index automatically on first run. The index data is stored under `data/activity_faiss/`.

4. Run the FastAPI server (from repository root or `server/`):

```powershell
cd server
uvicorn server.api.main:app --host 0.0.0.0 --port 8001 --reload
```

The server exposes a health endpoint and the main chat/orchestrator endpoint (see API section below).

Quick start — client (development)
1. Install and start the frontend dev server:

```powershell
cd client
npm install
npm run dev
```

2. By default the frontend expects the backend to be reachable by the address allowed in CORS (the server currently allows `http://localhost:5173` by default). Adjust `server/api/main.py` CORS settings if you run the client on a different port.

API (important endpoints)
- `GET /health` — health check (returns JSON with status).
- `POST /api/chat` — main entry point. Accepts a JSON body matching `UserQuerySchema` in `server/schemas/userQuery_schema.py` (typically `{ "query": "..." }`) and returns a structured response containing the generated summary and intermediate status.

Data & indexes
- `data/activity_faiss/` — FAISS index used by the activity agent.
- `data/orchestrator_chroma/` — Chroma DB used by the orchestrator (if present).

Development notes
- Agents are implemented as modular Python packages under `server/agents/`. Each agent exposes functions used by the workflow; the orchestrator builds a graph of agent steps in `server/workflow/graph_builder.py`.
- The project uses LangChain-style integrations and local vector stores. Check the agents for details on how they fetch or refresh vector indexes and how they call LLMs.
- The frontend can call gateway endpoints directly or use agent-specific proxy endpoints mounted under `/agents/<agent_name>` (see `client/README.md`).

Testing
- Unit tests are under `server/test/`. Run tests from the `server` folder after installing test dependencies:

```powershell
cd server
# activate venv first
pip install pytest
pytest -q
```

Security & operational notes
- Keep API keys and secrets out of source control. Use environment variables or a secrets manager.
- LLM calls may incur cost — configure model selection and temperature in `server/utils/config.py`.
- Be mindful of rate limits and token usage when running large batches of requests.

Suggested next steps and improvements
- Add `.env.example` documenting required environment variables.
- Add CI that validates the FAISS build and runs unit tests.
- Improve agent discovery so the frontend can list available agents dynamically.

Contributing
- Please open issues or pull requests. Provide small, focused changes and include tests for new behavior.

Maintainers / contributors
- Dulhara Kaushalya — https://github.com/dulhara79
- Senuvi Layathma — https://github.com/SENUVI20
- Dewdu Sendanayake — https://github.com/DewduSendanayake
- Uvindu Seneviratne — https://github.com/UVINDUSEN

License
- MIT — see `LICENSE` file for details.
