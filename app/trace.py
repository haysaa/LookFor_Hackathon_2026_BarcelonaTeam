"""
Trace logging utilities for observability.
Every agent decision and tool call is logged here.
"""
from typing import Any, Optional
from app.models import TraceEvent, TraceEventType
from app.store import session_store


class TraceLogger:
    """
    Centralized trace logging.
    All agent decisions and tool calls go through here.
    """
    
    @staticmethod
    def log(
        session_id: str,
        event_type: TraceEventType,
        agent: Optional[str] = None,
        **data: Any
    ) -> TraceEvent:
        """
        Log a trace event to the session.
        
        Args:
            session_id: The session to log to
            event_type: Type of event (triage, workflow, tool, etc.)
            agent: Name of the agent producing this event
            **data: Arbitrary data to include in the trace
        
        Returns:
            The created TraceEvent
        """
        event = TraceEvent(
            event_type=event_type,
            agent=agent,
            data=data
        )
        session_store.add_trace_event(session_id, event)
        return event
    
    @staticmethod
    def log_customer_message(session_id: str, message: str) -> TraceEvent:
        """Log an incoming customer message."""
        return TraceLogger.log(
            session_id,
            TraceEventType.CUSTOMER_MESSAGE,
            message=message
        )
    
    @staticmethod
    def log_triage_result(
        session_id: str,
        intent: str,
        confidence: float,
        entities: dict[str, Any]
    ) -> TraceEvent:
        """Log triage agent result."""
        return TraceLogger.log(
            session_id,
            TraceEventType.TRIAGE_RESULT,
            agent="triage",
            intent=intent,
            confidence=confidence,
            entities=entities
        )
    
    @staticmethod
    def log_workflow_decision(
        session_id: str,
        workflow_id: str,
        next_action: str,
        policy_applied: list[str],
        required_fields_missing: Optional[list[str]] = None,
        tool_plan: Optional[list[str]] = None
    ) -> TraceEvent:
        """Log workflow engine decision."""
        return TraceLogger.log(
            session_id,
            TraceEventType.WORKFLOW_DECISION,
            agent="workflow",
            workflow_id=workflow_id,
            next_action=next_action,
            policy_applied=policy_applied,
            required_fields_missing=required_fields_missing or [],
            tool_plan=tool_plan or []
        )
    
    @staticmethod
    def log_tool_call(
        session_id: str,
        tool_name: str,
        params: dict[str, Any],
        response: dict[str, Any],
        success: bool,
        retry_count: int = 0
    ) -> TraceEvent:
        """Log a tool call with its result."""
        return TraceLogger.log(
            session_id,
            TraceEventType.TOOL_CALL,
            agent="action",
            tool_name=tool_name,
            params=params,
            response=response,
            success=success,
            retry_count=retry_count
        )
    
    @staticmethod
    def log_agent_response(
        session_id: str,
        agent: str,
        response: str,
        subject: Optional[str] = None
    ) -> TraceEvent:
        """Log an agent-generated response."""
        return TraceLogger.log(
            session_id,
            TraceEventType.AGENT_RESPONSE,
            agent=agent,
            response=response,
            subject=subject
        )
    
    @staticmethod
    def log_escalation(
        session_id: str,
        reason: str,
        payload: dict[str, Any]
    ) -> TraceEvent:
        """Log an escalation event."""
        return TraceLogger.log(
            session_id,
            TraceEventType.ESCALATION,
            agent="escalation",
            reason=reason,
            payload=payload
        )
    
    @staticmethod
    def log_error(
        session_id: str,
        agent: str,
        error: str,
        details: Optional[dict[str, Any]] = None
    ) -> TraceEvent:
        """Log an error event."""
        return TraceLogger.log(
            session_id,
            TraceEventType.ERROR,
            agent=agent,
            error=error,
            details=details or {}
        )
