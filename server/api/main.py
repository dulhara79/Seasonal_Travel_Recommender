from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from server.api.route import router as api_router
from server.api.auth import router as auth_router
from server.api.conversations import router as conversations_router
from server.utils.db import connect_to_mongo, close_mongo_connection
import uvicorn
import os

app = FastAPI(title="Seasonal Travel Recommender API")

CORS_ORIGINS = os.environ.get("CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
).split(",")

origins = [origin.strip() for origin in CORS_ORIGINS] + [
    "http://localhost",
    "http://localhost:5173",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(api_router, prefix="/api")
app.include_router(conversations_router, prefix="/api/conversations")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Seasonal Travel Recommender API"}

@app.on_event("startup")
async def startup_event():
    # Attempt to connect to MongoDB and log status
    try:
        await connect_to_mongo()
        print("[SUCCESS] Server initialization complete. MongoDB connection verified.")
    except Exception as e:
        print(f"ERROR: Failed to connect to MongoDB: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    print("[INFO] Server shutdown complete.")

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    # Ensure uvicorn is imported if running directly
    if 'uvicorn' in locals() or 'uvicorn' in globals():
        uvicorn.run("server.api.main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        print("Uvicorn not imported. Run the application using 'uvicorn server.api.main:app --reload'")
