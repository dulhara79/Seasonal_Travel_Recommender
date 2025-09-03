# Client (Frontend)

This frontend is a small React app (Vite) that provides pages for Conversation and Summary.

How the frontend uses agents
- The gateway mounts agents under `/agents/<agent_name>` when the server is running.
- The Conversation page sends a POST to `/agents/summary_agent/summarize` with body { text: string } and expects JSON with `markdown` or `summary` containing markdown text.
- If the network request fails, the Conversation page will treat the typed/pasted input as markdown and display it locally.

Files added
- `src/pages/Conversation.jsx`: conversation UI and summary request logic.
- `src/pages/Summary.jsx`: renders markdown provided by the app state.
- `src/components/SummaryViewer.jsx`: renders markdown using `react-markdown`.

Run locally
1. Install dependencies in `client`:

```powershell
cd client; npm install
```

2. Start dev server:

```powershell
npm run dev
```

Notes
- The gateway's `routes.py` exposes convenience endpoints (e.g., `/chat`) which proxy to the `convo_orchestrator`. The frontend can also call those directly.
- This client intentionally keeps the UI lightweight. Improvements: add authentication headers, agent discovery (call `/health`), and nicer styling.
