

# Seasonal Travel Recommender
> Seasonal Travel Recommender - Orchestrator, Location Agent, Activity Suggestor, Packing List Generator, Summary Agent

A lightweight multi-agent travel assistant that combines location, activity suggestions, and packing-list generation to help travellers plan short trips. The project is implemented as a FastAPI backend (agents) and a small React + Vite frontend.

Overview
- Purpose: Given a free-text user request (destination, dates, preferences), the system extracts trip details, fetches or reasons about weather, suggests activities tailored to the forecast and preferences, and produces a concise packing list and a friendly trip summary.
- Audience: demo projects, coursework, and a starting point for building more advanced travel assistants.

Quick architecture
- Frontend (client): React + Vite app in `client/` that presents a Conversation UI and Summary view.
- Backend (server): FastAPI app in `server/` exposing `/api` endpoints and orchestrating a small workflow of agents using a state graph.
- Agents: modular Python functions that implement responsibilities such as orchestrating user input, suggesting activities (RAG + LLM), and creating a final markdown summary.

Text diagram

Client (React) ←→ FastAPI gateway (/api) → Workflow (orchestrator → activity_agent → summary_agent)

Key components
- `server/api/main.py` — FastAPI app with CORS and health endpoint.
- `server/api/route.py` — Exposes `/api/chat` which runs the workflow (uses `server.workflow.graph_builder.build_graph`).
- `server/workflow/graph_builder.py` — Builds a StateGraph connecting `orchestrator_agent` → `activity_agent` → `summary_agent`.
- `server/agents/orchestrator_agent/orchestrator_agent.py` — LLM-based extractor to parse user queries (destination, dates, preferences) and optionally ask follow-up questions.
- `server/agents/activity_agent_1/activity_agent.py` — RAG-backed activity suggester (FAISS index + OpenAI embeddings + LLM fallback).
- `server/agents/summary_agent/summary_agent.py` — Polishes collected details into a friendly Markdown trip summary using the LLM.

Repository layout (short)
- client/ — React frontend (Vite). See `client/README.md` for details.
- server/ — FastAPI backend, agents, workflows, and schemas.
- data/ — Prebuilt vector stores and Chroma DB used by agents (`data/activity_faiss`, `data/orchestrator_chroma`).

Requirements (selected)
- Python (3.10+ recommended)
- See `server/requirements.txt` for Python dependencies (FastAPI, Uvicorn, LangChain, OpenAI bindings, FAISS support, etc.).
- Node.js + npm (for the frontend). See `client/package.json`.

Local setup & run (server)
1. Create a Python virtual environment and activate it.

```powershell
cd server
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Provide LLM credentials and configuration. The code references `server/utils/config.py` and environment variables such as `OPENAI_API_KEY` and `LLM_MODEL`. Create a `.env` or export the variables in your shell (do NOT commit secrets):

```powershell
$env:OPENAI_API_KEY = "sk-..."
$env:LLM_MODEL = "gpt-4o-mini"  ; # or another supported model
```

3. (Optional) Build the activity FAISS index the first time the activity agent runs; the agent will build it automatically if missing. You can pre-build by running a small Python script that calls `build_or_refresh_index()` from `server/agents/activity_agent_1/activity_agent.py`.

4. Start the FastAPI server (from the `server` directory):

```powershell
# from repository root
cd server
uvicorn server.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The server exposes `/health` and `POST /api/chat`.

Local setup & run (client)
1. Install dependencies and start Vite dev server:

```powershell
cd client
npm install
npm run dev
```

2. The client expects the backend to be available on the address allowed in CORS (`http://localhost:5173` is allowed in `server/api/main.py`). The client calls the gateway endpoints (see `client/src/pages/Conversation.jsx`).

API (important endpoints)
- GET /health — Simple health check returning {"status": "ok"}.
- POST /api/chat — Accepts a JSON body matching `UserQuerySchema` (see `server/schemas/userQuery_schema.py`) with a `query` string. The server runs the workflow and returns `{ query, output: { summary, status, format } }` where `summary` is Markdown produced by the agents.

Data & indexes
- `data/activity_faiss/` — FAISS index used by the activity agent. The agent will create or refresh this index from web sources when needed.
- `data/orchestrator_chroma/` — Chroma DB used by orchestrator agent (if present).

Testing
- Unit tests are under `server/test/`. Run them with pytest from the `server` directory after setting environment variables and dependencies.

```powershell
cd server
# activate venv first
pip install pytest
pytest -q
```

Notes, limitations & security
- Secrets: keep API keys out of source control. Use environment variables or a secrets manager.
- Cost & rate limits: LLM calls may incur cost; configure model and temperature in `server/utils/config.py`.
- Fallbacks: several agents include LLM parsing fallbacks and heuristics (e.g., activity agent provides simple suggestions if RAG/LLM output isn't strict JSON).
- Missing files: some placeholders exist (e.g., agent modules with minimal content) — check the `server/agents` folder and tests to see intended behavior.

Developer notes & next steps
- Improve agent discovery and gateway proxying so the frontend can automatically list available agents.
- Add an optional CLI runner for the orchestrator for offline testing (the orchestrator agent supports interactive follow-ups in `call_orchestrator_agent`).
- Add proper tests for the RAG pipeline and LLM outputs; include CI that verifies the FAISS index build step is reproducible.

Contributing
- Please open issues and PRs. Keep commits small and document any added external data sources. Add `.env.example` entries for required environment variables.

Maintainers / contributors
- Dulhara Kaushalya — https://github.com/dulhara79
- Senuvi Layathma — https://github.com/SENUVI20
- Dewdu Sendanayake — https://github.com/DewduSendanayake
- Uvindu Seneviratne — https://github.com/UVINDUSEN

License
- MIT — see `LICENSE` file.

If you want, I can now commit this README update to the repository (I will overwrite the current `README.md`) and then run a quick verification read-back. Say "Apply README" to proceed.
