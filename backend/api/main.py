"""
File location in project: api/main.py
    uvicorn api.main:app --reload
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.state import AppState
from api.routers import alerts, analytics, incidents, knowledge_base, live, overview


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 70)
    print("ARIA API -- loading agents (this can take a little while) ...")
    print("=" * 70)
    app.state.aria = AppState()
    yield
    print("ARIA API shutting down.")


app = FastAPI(title="ARIA API", description="Alert Ranking & Intelligence Agent", lifespan=lifespan)

_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(overview.router)
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(incidents.router)
app.include_router(knowledge_base.router)
app.include_router(live.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=int(os.environ.get("API_PORT", "8000")),
        reload=True,
    )
