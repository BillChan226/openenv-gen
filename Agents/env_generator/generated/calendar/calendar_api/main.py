from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from calendar_api.database import init_db


# Define allowed CORS origins; can be customized via environment/config later
DEFAULT_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context.

    Used for startup and shutdown events. Initializes the database schema on
    startup. Any cleanup logic can be added on shutdown.
    """
    # Startup: initialize database tables
    init_db()
    yield
    # Shutdown: add cleanup logic here if needed


app = FastAPI(
    title="Calendar API",
    description="Backend API for the calendar application.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from calendar_api.routers import auth
app.include_router(auth.router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """
    Lightweight health check endpoint.

    Does not touch the database; intended for liveness checks.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "calendar_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )