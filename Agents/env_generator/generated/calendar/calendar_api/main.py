from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import auth


from routers.auth import router as auth_router

app = FastAPI(
    title="Calendar API",
    description="Backend API for the calendar application.",
    version="1.0.0",
)


# CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    """Application startup event."""
    init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("calendar_api.main:app", host="0.0.0.0", port=8000, reload=True)
