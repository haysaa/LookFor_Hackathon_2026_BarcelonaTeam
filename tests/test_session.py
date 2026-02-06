"""
Unit tests for SessionStore.
"""
import pytest
from app.models import CustomerInfo, SessionStatus, Message, MessageRole, TraceEvent, TraceEventType
from app.store import SessionStore


class TestSessionStore:
    """Unit tests for in-memory session store."""
    
    def setup_method(self):
        """Create fresh store for each test."""
        self.store = SessionStore()
        self.customer_info = CustomerInfo(
            customer_email="test@example.com",
            first_name="Test",
            last_name="User",
            shopify_customer_id="cust_123"
        )
    
    def test_create_session(self):
        """Creating a session returns a valid Session object."""
        session = self.store.create(self.customer_info)
        assert session.id is not None
        assert session.status == SessionStatus.ACTIVE
        assert session.customer_info.first_name == "Test"
    
    def test_get_session(self):
        """Can retrieve a created session by ID."""
        session = self.store.create(self.customer_info)
        retrieved = self.store.get(session.id)
        assert retrieved is not None
        assert retrieved.id == session.id
    
    def test_get_nonexistent_session(self):
        """Getting non-existent session returns None."""
        result = self.store.get("nonexistent")
        assert result is None
    
    def test_add_message(self):
        """Can add a message to a session."""
        session = self.store.create(self.customer_info)
        message = Message(role=MessageRole.CUSTOMER, content="Hello")
        
        updated = self.store.add_message(session.id, message)
        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Hello"
    
    def test_add_trace_event(self):
        """Can add a trace event to a session."""
        session = self.store.create(self.customer_info)
        event = TraceEvent(
            event_type=TraceEventType.CUSTOMER_MESSAGE,
            data={"message": "test"}
        )
        
        updated = self.store.add_trace_event(session.id, event)
        assert len(updated.trace) == 1
    
    def test_set_status_escalated(self):
        """Can set session status to escalated."""
        session = self.store.create(self.customer_info)
        
        updated = self.store.set_status(session.id, SessionStatus.ESCALATED)
        assert updated.status == SessionStatus.ESCALATED
    
    def test_is_escalated(self):
        """is_escalated returns correct status."""
        session = self.store.create(self.customer_info)
        
        assert self.store.is_escalated(session.id) is False
        
        self.store.set_status(session.id, SessionStatus.ESCALATED)
        assert self.store.is_escalated(session.id) is True
    
    def test_escalated_guard(self):
        """Escalated session should be locked."""
        session = self.store.create(self.customer_info)
        self.store.set_status(session.id, SessionStatus.ESCALATED)
        
        # Session is locked - no new messages should be processed
        # (This is enforced in Orchestrator, here we just check status)
        assert self.store.is_escalated(session.id) is True
