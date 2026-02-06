"""
LookFor Hackathon 2026 - Multi-Agent Customer Support System
Entry point for FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="LookFor Support Agent",
    description="Multi-agent customer support system for WISMO, Refund, and Wrong/Missing Item use cases",
    version="1.0.0"
)

# CORS middleware (for demo/testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api import router as session_router
app.include_router(session_router, tags=["Sessions"])


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "LookFor Support Agent",
        "version": "1.0.0",
        "endpoints": {
            "start_session": "POST /session/start",
            "send_message": "POST /session/{id}/message",
            "get_trace": "GET /session/{id}/trace"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
