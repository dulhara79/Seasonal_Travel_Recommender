from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from server.api.route import router

app = FastAPI()

# allowed origins for CORS
origins = [
    "http://localhost:5173"
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

# add route to check if server is running
@app.get("/health")
def health_check():
    return {"status": "ok"}
