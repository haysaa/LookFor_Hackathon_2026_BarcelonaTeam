"""
Data models for the multi-agent customer support system.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


class SessionStatus(str, Enum):
    """Session lifecycle states."""
    ACTIVE = "active"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class Intent(str, Enum):
    """Supported customer intents."""
    WISMO = "WISMO"  # Where Is My Order / Shipping Delay
    WRONG_MISSING = "WRONG_MISSING"  # Wrong or Missing Item
    REFUND_STANDARD = "REFUND_STANDARD"  # Standard Refund Request
    UNKNOWN = "UNKNOWN"


class MessageRole(str, Enum):
    """Message sender roles."""
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"


class Message(BaseModel):
    """A single message in the conversation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TraceEventType(str, Enum):
    """Types of trace events for observability."""
    CUSTOMER_MESSAGE = "customer_message"
    TRIAGE_RESULT = "triage_result"
    WORKFLOW_DECISION = "workflow_decision"
    TOOL_CALL = "tool_call"
    AGENT_RESPONSE = "agent_response"
    ESCALATION = "escalation"
    ERROR = "error"


class TraceEvent(BaseModel):
    """A single trace event for observability."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: TraceEventType
    agent: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CustomerInfo(BaseModel):
    """Customer information for session creation."""
    customer_email: str
    first_name: str
    last_name: str
    shopify_customer_id: str


class CaseContext(BaseModel):
    """Context extracted during conversation for workflow decisions."""
    order_id: Optional[str] = None
    tracking_number: Optional[str] = None
    item_name: Optional[str] = None
    refund_reason: Optional[str] = None
    order_date: Optional[str] = None
    shipping_status: Optional[str] = None
    evidence: dict[str, bool] = Field(default_factory=lambda: {
        "item_photo": False,
        "packing_slip": False,
        "shipping_label": False
    })
    promise_given: bool = False
    promise_date: Optional[str] = None
    contact_day: Optional[str] = None  # Mon, Tue, Wed, etc.
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """Record of a tool invocation."""
    tool_name: str
    params: dict[str, Any]
    response: Optional[dict[str, Any]] = None
    success: bool = False
    retry_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """Complete session state."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_info: CustomerInfo
    status: SessionStatus = SessionStatus.ACTIVE
    intent: Optional[Intent] = None
    confidence: float = 0.0
    messages: list[Message] = Field(default_factory=list)
    case_context: CaseContext = Field(default_factory=CaseContext)
    tool_history: list[ToolCall] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# --- API Request/Response Models ---

class SessionStartRequest(BaseModel):
    """Request body for POST /session/start."""
    customer_email: str
    first_name: str
    last_name: str
    shopify_customer_id: str


class SessionStartResponse(BaseModel):
    """Response for POST /session/start."""
    session_id: str
    status: SessionStatus
    message: str


class MessageRequest(BaseModel):
    """Request body for POST /session/{id}/message."""
    message: str


class MessageResponse(BaseModel):
    """Response for POST /session/{id}/message."""
    session_id: str
    status: SessionStatus
    reply: str
    intent: Optional[Intent] = None
    trace_event_count: int


class TraceResponse(BaseModel):
    """Response for GET /session/{id}/trace."""
    session_id: str
    status: SessionStatus
    events: list[TraceEvent]
    total_events: int


# --- Escalation Schema (Required Format) ---

class EscalationPayload(BaseModel):
    """
    Structured escalation payload for internal team.
    Must conform to the required schema in sprint plan.
    """
    escalation_id: str = Field(default_factory=lambda: f"esc_{uuid.uuid4().hex[:8]}")
    customer_id: str
    reason: str
    conversation_summary: str
    attempted_actions: list[str] = Field(default_factory=list)
    priority: str = "medium"  # low | medium | high
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
