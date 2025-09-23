from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from server.api.route import router as api_router
from server.api.auth import router as auth_router
from server.utils.db import connect_to_mongo, close_mongo_connection
import uvicorn

app = FastAPI(title="Seasonal Travel Recommender API")

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    # Avoid non-ASCII emoji in logs which can trigger UnicodeEncodeError on
    # Windows consoles using cp1252. Use plain ASCII messages instead.
    print("Server started and MongoDB connected.")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("Server shutdown")

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("server.api.main:app", host="0.0.0.0", port=8000, reload=False)
