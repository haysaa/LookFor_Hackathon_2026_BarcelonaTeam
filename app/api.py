"""
FastAPI endpoints for the multi-agent customer support system.
"""
from fastapi import APIRouter, HTTPException
from app.models import (
    SessionStartRequest, SessionStartResponse,
    MessageRequest, MessageResponse,
    TraceResponse, CustomerInfo, SessionStatus
)
from app.store import session_store
from app.orchestrator import orchestrator

router = APIRouter()


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(request: SessionStartRequest):
    """
    Create a new customer support session.
    
    Returns a session ID to use for subsequent message calls.
    """
    customer_info = CustomerInfo(
        customer_email=request.customer_email,
        first_name=request.first_name,
        last_name=request.last_name,
        shopify_customer_id=request.shopify_customer_id
    )
    
    session = session_store.create(customer_info)
    
    return SessionStartResponse(
        session_id=session.id,
        status=session.status,
        message=f"Merhaba {request.first_name}, size nasıl yardımcı olabilirim?"
    )


@router.post("/session/{session_id}/message", response_model=MessageResponse)
async def send_message(session_id: str, request: MessageRequest):
    """
    Send a customer message and get an agent response.
    
    The message is processed through the orchestrator which coordinates:
    - Triage Agent (intent classification)
    - Workflow Engine (policy decisions)
    - Action Agent (tool execution)
    - Support Agent (response generation)
    - Escalation Agent (if needed)
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    result = orchestrator.process_message(session_id, request.message)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return MessageResponse(
        session_id=session_id,
        status=result.get("status", SessionStatus.ACTIVE),
        reply=result.get("reply", ""),
        intent=result.get("intent"),
        trace_event_count=result.get("trace_event_count", 0)
    )


@router.get("/session/{session_id}/trace", response_model=TraceResponse)
async def get_trace(session_id: str):
    """
    Get the trace timeline for a session.
    
    Returns all agent decisions, tool calls, and events for observability.
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return TraceResponse(
        session_id=session_id,
        status=session.status,
        events=session.trace,
        total_events=len(session.trace)
    )


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Get the full session state (for debugging).
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "lookfor-support-agent"}
