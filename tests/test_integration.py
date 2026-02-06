"""
Integration tests for multi-agent flow.
Tests end-to-end customer message processing.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from app.store import session_store


client = TestClient(app)


class TestIntegrationFlow:
    """Integration tests for multi-agent orchestration."""
    
    def setup_method(self):
        """Clear session store before each test."""
        session_store.clear()
    
    def _create_session(self) -> str:
        """Helper to create a test session."""
        response = client.post("/session/start", json={
            "customer_email": "integration@test.com",
            "first_name": "Test",
            "last_name": "User",
            "shopify_customer_id": "cust_integration_123"
        })
        return response.json()["session_id"]
    
    # --- WISMO Flow Tests ---
    
    def test_wismo_flow_monday_friday_promise(self):
        """
        WISMO on Monday should give Friday promise.
        Flow: Message → Triage(stub) → Workflow → Response
        """
        session_id = self._create_session()
        
        # Simulate WISMO query with order_id
        # Since triage is stubbed, we need to set intent manually
        session = session_store.get(session_id)
        from app.models import Intent
        session.intent = Intent.WISMO
        session.case_context.order_id = "ORD-12345"
        session.case_context.contact_day = "Mon"
        session_store.update(session)
        
        # Send message
        response = client.post(f"/session/{session_id}/message", json={
            "message": "Siparişim nerede? Sipariş numaram ORD-12345"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should get Friday promise
        assert "Cuma" in data["reply"]
        assert data["trace_event_count"] > 0
    
    def test_wismo_flow_thursday_next_week_promise(self):
        """WISMO on Thursday should give next week promise."""
        session_id = self._create_session()
        
        session = session_store.get(session_id)
        from app.models import Intent
        session.intent = Intent.WISMO
        session.case_context.order_id = "ORD-67890"
        session.case_context.contact_day = "Thu"
        session_store.update(session)
        
        response = client.post(f"/session/{session_id}/message", json={
            "message": "Siparişim gelmedi"
        })
        
        assert response.status_code == 200
        assert "hafta" in response.json()["reply"].lower()
    
    # --- Wrong/Missing Flow Tests ---
    
    def test_wrong_missing_asks_for_evidence(self):
        """Wrong/Missing without evidence should ask for photos."""
        session_id = self._create_session()
        
        session = session_store.get(session_id)
        from app.models import Intent
        session.intent = Intent.WRONG_MISSING
        session.case_context.order_id = "ORD-11111"
        session.case_context.item_name = "Blue T-Shirt"
        # Evidence is False by default
        session_store.update(session)
        
        response = client.post(f"/session/{session_id}/message", json={
            "message": "Paketimden ürün eksik çıktı"
        })
        
        assert response.status_code == 200
        reply = response.json()["reply"]
        # Should ask for evidence
        assert "fotoğraf" in reply.lower() or "paylaşır" in reply.lower()
    
    def test_wrong_missing_with_evidence_escalates(self):
        """Wrong/Missing with complete evidence should escalate for reship."""
        session_id = self._create_session()
        
        session = session_store.get(session_id)
        from app.models import Intent
        session.intent = Intent.WRONG_MISSING
        session.case_context.order_id = "ORD-22222"
        session.case_context.item_name = "Red Dress"
        session.case_context.evidence = {
            "item_photo": True,
            "packing_slip": True,
            "shipping_label": True
        }
        session_store.update(session)
        
        response = client.post(f"/session/{session_id}/message", json={
            "message": "İşte fotoğraflar, yanlış ürün geldi"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should escalate
        assert data["status"] == "escalated"
        assert "24 saat" in data["reply"]
    
    # --- Refund Flow Tests ---
    
    def test_refund_shipping_delay_routes_to_wismo(self):
        """Refund due to shipping delay should route to WISMO."""
        session_id = self._create_session()
        
        session = session_store.get(session_id)
        from app.models import Intent
        session.intent = Intent.REFUND_STANDARD
        session.case_context.order_id = "ORD-33333"
        session.case_context.refund_reason = "shipping_delay"
        session.case_context.contact_day = "Tue"
        session_store.update(session)
        
        response = client.post(f"/session/{session_id}/message", json={
            "message": "Refund istiyorum, kargo gecikmesi var"
        })
        
        assert response.status_code == 200
        # Should route to WISMO and give Friday promise (since Tue)
        assert "Cuma" in response.json()["reply"]
    
    # --- Escalation & Lock Tests ---
    
    def test_escalated_session_is_locked(self):
        """Escalated session should reject new messages with lock message."""
        session_id = self._create_session()
        
        # Escalate the session
        from app.models import SessionStatus
        session_store.set_status(session_id, SessionStatus.ESCALATED)
        
        # Try to send a message
        response = client.post(f"/session/{session_id}/message", json={
            "message": "Ne oldu?"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "escalated"
        # Should get lock message, not process the new query
        assert "uzman" in data["reply"].lower() or "iletilmiş" in data["reply"].lower()
    
    # --- Trace Tests ---
    
    def test_trace_contains_all_steps(self):
        """Trace should contain customer message, triage, workflow, response."""
        session_id = self._create_session()
        
        session = session_store.get(session_id)
        from app.models import Intent
        session.intent = Intent.WISMO
        session.case_context.order_id = "ORD-TRACE"
        session.case_context.contact_day = "Mon"
        session_store.update(session)
        
        client.post(f"/session/{session_id}/message", json={
            "message": "Siparişim nerede?"
        })
        
        # Get trace
        trace_response = client.get(f"/session/{session_id}/trace")
        assert trace_response.status_code == 200
        
        events = trace_response.json()["events"]
        event_types = [e["event_type"] for e in events]
        
        # Should have key events
        assert "customer_message" in event_types
        assert "triage_result" in event_types
        assert "workflow_decision" in event_types
        assert "agent_response" in event_types
