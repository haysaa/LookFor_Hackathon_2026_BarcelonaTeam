"""
Unit tests for Escalation Agent.
Tests escalation payload schema and session locking.
"""
import pytest
from app.agents.escalation import EscalationAgent
from app.store import session_store
from app.models import CustomerInfo, SessionStatus, Intent


class TestEscalationAgent:
    """Unit tests for EscalationAgent."""
    
    def setup_method(self):
        """Setup test fixtures."""
        session_store.clear()
        
        self.customer = CustomerInfo(
            customer_email="test@example.com",
            first_name="Test",
            last_name="User",
            shopify_customer_id="cust_123"
        )
        self.session = session_store.create(self.customer)
        self.agent = EscalationAgent()
    
    def test_escalation_payload_schema(self):
        """Escalation payload matches required schema."""
        result = self.agent.escalate(
            session_id=self.session.id,
            reason="Test escalation reason"
        )
        
        payload = result["escalation_payload"]
        
        # Check required fields from schema
        assert "escalation_id" in payload
        assert payload["escalation_id"].startswith("esc_")
        assert "customer_id" in payload
        assert payload["customer_id"] == "cust_123"
        assert "reason" in payload
        assert payload["reason"] == "Test escalation reason"
        assert "conversation_summary" in payload
        assert "attempted_actions" in payload
        assert isinstance(payload["attempted_actions"], list)
        assert "priority" in payload
        assert payload["priority"] in ["low", "medium", "high"]
        assert "created_at" in payload
    
    def test_session_locked_after_escalation(self):
        """Session status is set to ESCALATED after escalation."""
        assert self.session.status == SessionStatus.ACTIVE
        
        self.agent.escalate(
            session_id=self.session.id,
            reason="Test"
        )
        
        updated = session_store.get(self.session.id)
        assert updated.status == SessionStatus.ESCALATED
    
    def test_customer_message_returned(self):
        """Escalation returns standard customer message."""
        result = self.agent.escalate(
            session_id=self.session.id,
            reason="Test"
        )
        
        assert "customer_message" in result
        assert "24 hours" in result["customer_message"]
    
    def test_priority_override(self):
        """Priority can be explicitly set."""
        result = self.agent.escalate(
            session_id=self.session.id,
            reason="Urgent issue",
            priority="high"
        )
        
        assert result["escalation_payload"]["priority"] == "high"
    
    def test_should_escalate_low_confidence(self):
        """Low confidence triggers escalation."""
        self.session.confidence = 0.4
        session_store.update(self.session)
        
        should, reason = self.agent.should_escalate(self.session)
        
        assert should is True
        assert "confidence" in reason.lower()
    
    def test_should_escalate_workflow_decision(self):
        """Workflow escalate decision triggers escalation."""
        decision = {
            "next_action": "escalate",
            "escalation_reason": "Policy requires human"
        }
        
        should, reason = self.agent.should_escalate(self.session, decision)
        
        assert should is True
        assert "Policy" in reason
    
    def test_escalation_logged_to_trace(self):
        """Escalation is logged to session trace."""
        initial_count = len(self.session.trace)
        
        self.agent.escalate(
            session_id=self.session.id,
            reason="Test"
        )
        
        updated = session_store.get(self.session.id)
        assert len(updated.trace) > initial_count
        
        # Find escalation event
        escalation_events = [e for e in updated.trace if e.event_type.value == "escalation"]
        assert len(escalation_events) == 1
