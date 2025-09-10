from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from server.api.route import router

app = FastAPI(title="Seasonal Travel Recommender API")

# allowed origins for CORS
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# register router
app.include_router(router, prefix="/api")

# health check route
@app.get("/health")
def health_check():
    return {"status": "ok"}

# startup event
@app.on_event("startup")
def startup_event():
    print(f"🚀 FastAPI server is running! Listening for requests... ")