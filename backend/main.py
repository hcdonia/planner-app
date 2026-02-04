"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .config import get_settings
from .api import chat_router, calendar_router, knowledge_router, settings_router, todos_router, files_router

settings = get_settings()

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="AI Planning Assistant",
    description="A self-evolving AI-powered planning and scheduling assistant",
    version="1.0.0",
)

# CORS middleware for frontend - allow all origins for now (can restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(calendar_router)
app.include_router(knowledge_router)
app.include_router(settings_router)
app.include_router(todos_router)
app.include_router(files_router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "AI Planning Assistant",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
