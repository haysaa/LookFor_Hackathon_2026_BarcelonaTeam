"""
Session Schema (Interface)
Version: 1.0
Developer: Dev B

Interface definition for Session State.
IMPLEMENTATION: Dev A

This defines the expected structure that Dev A will implement.
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class CustomerInfo(BaseModel):
    """Customer information for session."""
    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    is_vip: bool = False


class Message(BaseModel):
    """A single message in the conversation."""
    role: Literal["customer", "agent", "system"]
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class CaseContext(BaseModel):
    """Context accumulated during the case resolution."""
    order_id: Optional[str] = None
    order_date: Optional[str] = None
    shipping_status: Optional[str] = None
    tracking_number: Optional[str] = None
    item_name: Optional[str] = None
    refund_reason: Optional[str] = None
    evidence_provided: Dict[str, bool] = Field(default_factory=lambda: {
        "item_photo": False,
        "packing_slip": False,
        "shipping_label": False
    })
    promise_given: Optional[str] = None  # e.g., "friday", "next_week"
    contact_day: Optional[str] = None  # Mon, Tue, Wed, etc.


class TraceEvent(BaseModel):
    """A single trace event for observability."""
    agent: str
    action: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Session(BaseModel):
    """
    Session state model.
    
    IMPLEMENTATION: Dev A
    This is the interface definition for Dev B to depend on.
    """
    session_id: str
    customer_info: CustomerInfo
    messages: List[Message] = Field(default_factory=list)
    intent: Optional[str] = None
    case_context: CaseContext = Field(default_factory=CaseContext)
    tool_history: List[Dict[str, Any]] = Field(default_factory=list)
    trace: List[TraceEvent] = Field(default_factory=list)
    status: Literal["active", "resolved", "escalated"] = "active"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Interface for Session Store (Dev A will implement)
class ISessionStore:
    """
    Interface for session storage.
    Dev A implements this; Dev B depends on it.
    """
    
    def create(self, customer_info: CustomerInfo) -> Session:
        """Create a new session."""
        raise NotImplementedError
    
    def get(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        raise NotImplementedError
    
    def update(self, session: Session) -> Session:
        """Update existing session."""
        raise NotImplementedError
    
    def add_message(self, session_id: str, message: Message) -> Session:
        """Add message to session."""
        raise NotImplementedError
    
    def add_trace(self, session_id: str, event: TraceEvent) -> Session:
        """Add trace event to session."""
        raise NotImplementedError
    
    def set_status(self, session_id: str, status: str) -> Session:
        """Update session status."""
        raise NotImplementedError
