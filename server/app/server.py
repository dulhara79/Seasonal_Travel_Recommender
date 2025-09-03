from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import importlib
import os

load_dotenv()

def _import_agent_app(module_path: str):
	"""Try to import a FastAPI app object from the given module path.
	Returns the app object or None if not available.
	"""
	try:
		mod = importlib.import_module(module_path)
		return getattr(mod, "app", None)
	except Exception:
		return None


app = FastAPI(title="Seasonal Travel - Gateway", version="1.0.0")

# CORS configuration (optional, driven by env)
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
	app.add_middleware(
		CORSMiddleware,
		allow_origins=origins,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

# Mount known agent sub-apps if present
AGENTS = {
	"convo_orchestrator": "server.agents.convo_orchestrator.main",
	"weather_agent": "server.agents.weather_agent.main",
	"activity_agent": "server.agents.activity_agent.main",
	"summary_agent": "server.agents.summary_agent.main"
}

mounted = {}
for name, module_path in AGENTS.items():
	agent_app = _import_agent_app(module_path)
	if agent_app:
		mount_path = f"/agents/{name}"
		app.mount(mount_path, agent_app)
		mounted[name] = mount_path


@app.get("/")
def root():
	return {
		"service": "Seasonal Travel Gateway",
		"mounted_agents": mounted,
		"note": "Agents are mounted under /agents/<agent_name> when available. Use /routes for convenience endpoints.",
	}

# Import and include the convenience router (kept separate to make routes testable)
try:
	from .routes import router as routes_router
	app.include_router(routes_router, prefix="", tags=["gateway"])
except Exception:
	# routes may not be importable during some static checks; ignore gracefully
	pass
