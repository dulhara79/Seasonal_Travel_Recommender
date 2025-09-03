from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import importlib
from typing import Any, Dict

router = APIRouter()


class HealthOut(BaseModel):
	status: str
	services: Dict[str, Any] = {}


@router.get("/health", response_model=HealthOut)
def health():
	"""Basic health check. Reports which agents are importable/mounted."""
	agents = {}
	candidates = {
		"convo_orchestrator": "server.agents.convo_orchestrator.main",
		"weather_agent": "server.agents.weather_agent.main",
		"activity_agent": "server.agents.activity_agent.main",
		"summary_agent": "server.agents.summary_agent.main"
	}
	for name, modpath in candidates.items():
		try:
			mod = importlib.import_module(modpath)
			agents[name] = {"available": True, "has_app": hasattr(mod, "app")}
		except Exception as e:
			agents[name] = {"available": False, "error": str(e)}

	return HealthOut(status="ok", services=agents)


@router.post("/chat")
async def chat_proxy(payload: Dict[str, Any]):
	"""Proxy /chat to the convo_orchestrator's chat endpoint when available.
	Expects the same body as the orchestrator: { user_id, text }
	"""
	try:
		mod = importlib.import_module("server.agents.convo_orchestrator.main")
	except Exception:
		raise HTTPException(status_code=503, detail="convo_orchestrator not available")

	# Call the same function defined in that module if present
	chat_fn = getattr(mod, "chat", None)
	if not chat_fn:
		raise HTTPException(status_code=503, detail="convo_orchestrator.chat not available")

	# call and return result
	result = await chat_fn(payload)
	return result
