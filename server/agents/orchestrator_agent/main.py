# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from orchestrator_agent import OrchestratorAgent
from schemas import UserMessage

app = FastAPI()
agent = OrchestratorAgent()

@app.post("/chat")
def chat_endpoint(msg: UserMessage):
    response = agent.handle_message(msg)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
