"""Schemas package initialization."""
from .triage import TriageResult, Intent, ExtractedEntities, TRIAGE_RESULT_SCHEMA
from .workflow import WorkflowDecision, ToolPlan
from .escalation import (
    EscalationTicket,
    CustomerEscalationEmail,
    EscalationOutput,
    ESCALATION_TICKET_SCHEMA
)
from .session import (
    Session,
    CustomerInfo,
    Message,
    CaseContext,
    TraceEvent,
    ISessionStore
)

__all__ = [
    # Triage
    "TriageResult",
    "Intent", 
    "ExtractedEntities",
    "TRIAGE_RESULT_SCHEMA",
    # Workflow
    "WorkflowDecision",
    "ToolPlan",
    # Escalation
    "EscalationTicket",
    "CustomerEscalationEmail",
    "EscalationOutput",
    "ESCALATION_TICKET_SCHEMA",
    # Session
    "Session",
    "CustomerInfo",
    "Message",
    "CaseContext",
    "TraceEvent",
    "ISessionStore",
]
