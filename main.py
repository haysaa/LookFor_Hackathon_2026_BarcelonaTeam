"""
LookFor Hackathon 2026 - Multi-Agent Customer Support System
Entry point for FastAPI application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
import os

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

# Mount static files for demo UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    """Redirect to demo UI."""
    return RedirectResponse(url="/static/index.html")


@app.get("/api")
async def api_info():
    """API info endpoint."""
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

