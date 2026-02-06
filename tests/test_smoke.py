"""
Smoke tests for session endpoints.
Verifies basic endpoint functionality returns 200.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestSessionEndpoints:
    """Smoke tests for session API endpoints."""
    
    def test_health_check(self):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_start_session_success(self):
        """POST /session/start creates a session and returns 200."""
        response = client.post("/session/start", json={
            "customer_email": "test@example.com",
            "first_name": "Ali",
            "last_name": "Yılmaz",
            "shopify_customer_id": "cust_12345"
        })
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "active"
        assert "Ali" in data["message"]
    
    def test_send_message_success(self):
        """POST /session/{id}/message accepts message and returns response."""
        # First create a session
        create_resp = client.post("/session/start", json={
            "customer_email": "test@example.com",
            "first_name": "Ayşe",
            "last_name": "Demir",
            "shopify_customer_id": "cust_67890"
        })
        session_id = create_resp.json()["session_id"]
        
        # Send a message
        response = client.post(f"/session/{session_id}/message", json={
            "message": "Siparişim nerede?"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "reply" in data
        assert data["trace_event_count"] > 0
    
    def test_get_trace_success(self):
        """GET /session/{id}/trace returns trace events."""
        # Create session and send message
        create_resp = client.post("/session/start", json={
            "customer_email": "test@example.com",
            "first_name": "Mehmet",
            "last_name": "Kaya",
            "shopify_customer_id": "cust_11111"
        })
        session_id = create_resp.json()["session_id"]
        
        client.post(f"/session/{session_id}/message", json={
            "message": "Test message"
        })
        
        # Get trace
        response = client.get(f"/session/{session_id}/trace")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "events" in data
        assert data["total_events"] > 0
    
    def test_session_not_found(self):
        """Non-existent session returns 404."""
        response = client.post("/session/invalid-id/message", json={
            "message": "Test"
        })
        assert response.status_code == 404
    
    def test_trace_not_found(self):
        """Trace for non-existent session returns 404."""
        response = client.get("/session/invalid-id/trace")
        assert response.status_code == 404
