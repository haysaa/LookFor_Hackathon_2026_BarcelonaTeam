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
        message=f"Welcome {request.first_name}! How can I help you today?"
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


# ===== ADMIN POLICY OVERRIDE ENDPOINTS =====

from app.policy_overrides import get_policy_store
from app.agents.policy_parser import PolicyParserAgent
from pydantic import BaseModel
from typing import Optional, List


class PolicyOverrideRequest(BaseModel):
    """Request to create a policy override via natural language prompt"""
    prompt: str
    active: bool = True


class PolicyOverrideResponse(BaseModel):
    """Response after creating a policy override"""
    success: bool
    override_id: str
    parsed_policy: dict
    message: str


class PolicyListResponse(BaseModel):
    """List of all policy overrides"""
    overrides: List[dict]
    total: int


@router.post("/admin/policy-override", response_model=PolicyOverrideResponse)
async def create_policy_override(request: PolicyOverrideRequest):
    """
    Create a dynamic policy override using natural language.
    
    Example:
    {
      "prompt": "If a customer wants to update their address, don't update it directly. Mark as NEEDS_ATTENTION and escalate.",
      "active": true
    }
    
    The system will parse the prompt and modify workflow behavior accordingly.
    """
    try:
        # Parse the prompt using LLM
        parser = PolicyParserAgent()
        parsed = parser.parse(request.prompt)
        
        # Validate
        is_valid, error = parser.validate_override(parsed)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid policy: {error}")
        
        # Generate override ID
        workflow = parsed["target_workflow"]
        rule_pattern = parsed["rule_pattern"]
        override_id = f"{workflow.lower()}_{rule_pattern.lower()}"
        
        # Store the override
        store = get_policy_store()
        
        # Find matching rule_id from workflow (simple pattern match for now)
        # In production, you'd search the actual workflow JSON
        rule_id = f"{workflow.lower()}_{rule_pattern.replace(' ', '_')}"
        
        override = store.add_override(
            override_id=override_id,
            workflow=parsed["target_workflow"],
            rule_id=rule_id,
            override_action=parsed["action_override"],
            original_prompt=request.prompt,
            context_updates=parsed.get("context_updates", {}),
            tool_param_overrides=parsed.get("tool_param_overrides", {}),
            escalation_reason=parsed.get("escalation_reason"),
            response_template_override=parsed.get("response_template_override"),
            active=request.active
        )
        
        return PolicyOverrideResponse(
            success=True,
            override_id=override_id,
            parsed_policy=parsed,
            message=f"Policy override created successfully. {workflow} workflow will now {parsed['action_override']} for {rule_pattern}."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create override: {str(e)}")


@router.get("/admin/policy-override", response_model=PolicyListResponse)
async def list_policy_overrides(active_only: bool = False):
    """
    List all policy overrides.
    
    Query params:
    - active_only: If true, only return active overrides
    """
    store = get_policy_store()
    overrides = store.list_overrides(active_only=active_only)
    
    return PolicyListResponse(
        overrides=[o.to_dict() for o in overrides],
        total=len(overrides)
    )


@router.get("/admin/policy-override/{override_id}")
async def get_policy_override(override_id: str):
    """Get a specific policy override by ID"""
    store = get_policy_store()
    override = store.get_by_id(override_id)
    
    if not override:
        raise HTTPException(status_code=404, detail="Override not found")
    
    return override.to_dict()


@router.post("/admin/policy-override/{override_id}/toggle")
async def toggle_policy_override(override_id: str):
    """Toggle a policy override active/inactive"""
    store = get_policy_store()
    
    try:
        new_status = store.toggle_override(override_id)
        return {
            "success": True,
            "override_id": override_id,
            "active": new_status,
            "message": f"Override is now {'active' if new_status else 'inactive'}"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/admin/policy-override/{override_id}")
async def delete_policy_override(override_id: str):
    """Delete a policy override"""
    store = get_policy_store()
    
    success = store.remove_override(override_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Override not found")
    
    return {
        "success": True,
        "override_id": override_id,
        "message": "Override deleted successfully"
    }


@router.delete("/admin/policy-override")
async def clear_all_overrides():
    """Clear all policy overrides (use with caution!)"""
    store = get_policy_store()
    store.clear_all()
    
    return {
        "success": True,
        "message": "All policy overrides cleared"
    }
