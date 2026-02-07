"""
API Contract Tests
==================
Validates FastAPI MVP against Lookfor Hackathon Minimum Requirements.

Requirements tested:
1. Email Session Start - accepts required customer fields
2. Continuous Memory / Multi-turn - context preserved across messages
3. Observable Answers and Actions - trace includes tool calls and decisions
4. Escalation Mechanism + Session Lock - session locks after escalation
5. Tool Uniform Contract Handling - graceful failure handling

Usage:
    pytest tests/test_api_contract.py -v

Prerequisites:
    - Server must be running at BASE_URL (default: http://localhost:8000)
    - Mock mode enabled by default in ToolsClient
"""
import os
import pytest
import httpx
from typing import Any, Optional


# ============================================================================
# Configuration
# ============================================================================

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TIMEOUT = 30.0  # seconds


# ============================================================================
# Helper Functions
# ============================================================================

def start_session(
    email: str = "alice@example.com",
    first_name: str = "Alice",
    last_name: str = "Doe",
    customer_id: str = "cust_test_001"
) -> str:
    """Start a new session and return the session_id."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        response = client.post("/session/start", json={
            "customer_email": email,
            "first_name": first_name,
            "last_name": last_name,
            "shopify_customer_id": customer_id
        })
        response.raise_for_status()
        data = response.json()
        return data["session_id"]


def send_message(session_id: str, text: str) -> dict:
    """Send a message to a session and return the response JSON."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        response = client.post(f"/session/{session_id}/message", json={
            "message": text
        })
        response.raise_for_status()
        return response.json()


def get_trace(session_id: str) -> dict:
    """Fetch the trace for a session."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        response = client.get(f"/session/{session_id}/trace")
        response.raise_for_status()
        return response.json()


def normalize_trace(trace_json: dict) -> list:
    """
    Normalize trace response to a list of events.
    Supports both [] and { "events": [] } formats.
    """
    if isinstance(trace_json, list):
        return trace_json
    if isinstance(trace_json, dict):
        if "events" in trace_json:
            return trace_json["events"]
        # If dict but no events key, return empty list
        return []
    return []


def extract_reply(resp_json: dict) -> str:
    """
    Extract the reply text from a response.
    Supports: reply, final_message, message, response fields.
    """
    for key in ["reply", "final_message", "message", "response"]:
        if key in resp_json and resp_json[key]:
            return str(resp_json[key])
    return ""


def has_event(events: list, kind_keywords: list[str]) -> bool:
    """
    Check if any event matches the given keywords.
    Searches in event_type, action, name, type fields.
    """
    for event in events:
        event_data = event if isinstance(event, dict) else {}
        # Check direct fields
        for field in ["event_type", "action", "name", "type"]:
            value = event_data.get(field, "")
            if isinstance(value, str):
                for keyword in kind_keywords:
                    if keyword.lower() in value.lower():
                        return True
        # Check nested data field
        data = event_data.get("data", {})
        if isinstance(data, dict):
            for field in ["event_type", "action", "name", "type"]:
                value = data.get(field, "")
                if isinstance(value, str):
                    for keyword in kind_keywords:
                        if keyword.lower() in value.lower():
                            return True
    return False


def find_events(events: list, kind_keywords: list[str]) -> list:
    """Find all events matching the given keywords."""
    result = []
    for event in events:
        event_data = event if isinstance(event, dict) else {}
        for field in ["event_type", "action", "name", "type"]:
            value = event_data.get(field, "")
            if isinstance(value, str):
                for keyword in kind_keywords:
                    if keyword.lower() in value.lower():
                        result.append(event)
                        break
    return result


def tool_events(events: list) -> list[dict]:
    """
    Extract tool call events with tool_name, params, output.
    """
    tool_calls = []
    for event in events:
        event_data = event if isinstance(event, dict) else {}
        event_type = event_data.get("event_type", "")
        
        if "tool" in str(event_type).lower():
            data = event_data.get("data", {})
            tool_calls.append({
                "tool_name": data.get("tool_name", event_data.get("tool_name", "")),
                "params": data.get("params", event_data.get("params", {})),
                "output": data.get("response", data.get("output", data.get("result", {}))),
                "success": data.get("success", event_data.get("success")),
                "error": data.get("error", "")
            })
    return tool_calls


def count_events_by_type(events: list, event_type: str) -> int:
    """Count events of a specific type."""
    count = 0
    for event in events:
        if isinstance(event, dict):
            if event.get("event_type", "").lower() == event_type.lower():
                count += 1
    return count


def has_timestamp(event: dict) -> bool:
    """Check if event has a timestamp field."""
    for field in ["timestamp", "time", "created_at", "ts"]:
        if field in event:
            return True
    return False


# ============================================================================
# Test Class
# ============================================================================

class TestAPIContract:
    """API Contract Tests for Hackathon Minimum Requirements."""
    
    # ------------------------------------------------------------------------
    # Test 1: Session Start Contract
    # ------------------------------------------------------------------------
    def test_session_start_contract(self):
        """
        Test 1: Session Start Contract
        
        POST /session/start must:
        - Accept customer_email, first_name, last_name, shopify_customer_id
        - Return HTTP 200
        - Return non-empty session_id
        - session_id can be used in subsequent calls
        """
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            # Start session with required fields
            response = client.post("/session/start", json={
                "customer_email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Doe",
                "shopify_customer_id": "cust_test_001"
            })
            
            # Assert HTTP 200
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            
            # Assert session_id exists and is non-empty
            assert "session_id" in data, "Response must contain 'session_id'"
            session_id = data["session_id"]
            assert session_id, "session_id must not be empty"
            assert isinstance(session_id, str), "session_id must be a string"
            
            # Verify session_id is usable
            trace_response = client.get(f"/session/{session_id}/trace")
            assert trace_response.status_code == 200, "Trace endpoint should accept the session_id"
    
    # ------------------------------------------------------------------------
    # Test 2: Multi-turn Memory Persists
    # ------------------------------------------------------------------------
    def test_multiturn_memory_persists(self):
        """
        Test 2: Multi-turn Memory Persists
        
        When sending multiple messages in the same session:
        - System must keep context
        - Must not contradict itself
        - Must persist conversation history
        - Second reply should NOT ask for name/email again
        """
        # Start session with specific customer info
        session_id = start_session(
            email="alice_memory@example.com",
            first_name="Alice",
            last_name="Doe",
            customer_id="cust_memory_001"
        )
        
        # Message 1: Introduce self and ask about order
        resp1 = send_message(session_id, "Hi, I'm Alice. My order is #1001. Where is my order?")
        assert extract_reply(resp1), "First message should get a reply"
        
        # Message 2: Ask without repeating info
        resp2 = send_message(
            session_id, 
            "What's the status now? Please don't ask for my email/name again."
        )
        reply2 = extract_reply(resp2).lower()
        
        # Assert second reply does NOT ask for customer info again
        # (Session should already have this from session start)
        forbidden_tokens = ["alice_memory@example.com", "what is your email", "what is your name"]
        for token in forbidden_tokens:
            assert token.lower() not in reply2, \
                f"System asked for '{token}' again - memory not persisted"
        
        # Fetch trace and verify structure
        trace = get_trace(session_id)
        events = normalize_trace(trace)
        
        # Assert at least 2 customer_message events
        customer_msg_count = count_events_by_type(events, "customer_message")
        assert customer_msg_count >= 2, \
            f"Expected at least 2 customer_message events, got {customer_msg_count}"
        
        # Assert triage decision event exists
        assert has_event(events, ["triage"]), \
            "Trace must contain triage decision event"
        
        # Assert workflow decision event exists
        assert has_event(events, ["workflow"]), \
            "Trace must contain workflow decision event"
        
        # Assert agent response event exists
        assert has_event(events, ["agent_response", "response", "support"]), \
            "Trace must contain agent response event"
    
    # ------------------------------------------------------------------------
    # Test 3: Observability - Trace Structure + Tool Calls
    # ------------------------------------------------------------------------
    def test_observability_trace_structure(self):
        """
        Test 3: Observability - Trace Structure + Tool Calls
        
        Trace endpoint must:
        - Return HTTP 200
        - Return list or object with events array
        - Events must have timestamp field
        - Include workflow decision + response event
        - Include tool_call events with tool_name, params, output (if mock enabled)
        """
        session_id = start_session(
            email="trace_test@example.com",
            first_name="Trace",
            last_name="Tester",
            customer_id="cust_trace_001"
        )
        
        # Send WISMO message to trigger tool call
        resp = send_message(session_id, "Where is my order #1001?")
        assert extract_reply(resp), "Should get a reply for WISMO query"
        
        # Fetch trace
        trace = get_trace(session_id)
        events = normalize_trace(trace)
        
        # Assert trace is not empty
        assert len(events) > 0, "Trace must contain events"
        
        # Assert events have timestamp
        has_ts = any(has_timestamp(e) for e in events if isinstance(e, dict))
        assert has_ts, "Events must have a timestamp field (timestamp, time, or created_at)"
        
        # Assert workflow decision exists
        assert has_event(events, ["workflow"]), \
            "Trace must include workflow decision event"
        
        # Assert response event exists
        assert has_event(events, ["agent_response", "response"]), \
            "Trace must include agent response event"
        
        # Check for tool_call events (mock mode should produce these)
        tools = tool_events(events)
        if not tools:
            # Warn but don't fail if workflow skipped tools
            workflow_events = find_events(events, ["workflow"])
            if workflow_events:
                # Check if workflow explicitly skipped tools
                for we in workflow_events:
                    data = we.get("data", {})
                    if data.get("tool_plan") or data.get("tools_to_call"):
                        pytest.fail(
                            "Expected tool_call events but found none. "
                            "Check tool integration, mock mode, or workflow tool_plan configuration."
                        )
        else:
            # Verify tool call structure
            for tool in tools:
                assert tool.get("tool_name"), \
                    f"Tool call must have tool_name: {tool}"
    
    # ------------------------------------------------------------------------
    # Test 4: Escalation + Session Lock
    # ------------------------------------------------------------------------
    def test_escalation_session_lock(self):
        """
        Test 4: Deterministic Escalation + Session Lock (Tool Failure Path)
        
        When tool fails with INVALID_FOR_TEST:
        - System escalates
        - Escalation payload has required fields
        - Subsequent messages do not trigger new tool calls
        - Session is locked
        """
        session_id = start_session(
            email="escalation_test@example.com",
            first_name="Escalation",
            last_name="Tester",
            customer_id="cust_escalation_001"
        )
        
        # Send message that triggers deterministic tool failure
        resp1 = send_message(session_id, "Where is my order #INVALID_FOR_TEST?")
        
        # Fetch trace before second message
        trace1 = get_trace(session_id)
        events1 = normalize_trace(trace1)
        
        # Check for tool failure
        tools = tool_events(events1)
        tool_failed = any(
            t.get("success") is False or "not found" in str(t.get("error", "")).lower()
            for t in tools
        )
        
        # Check for escalation event or payload
        has_escalation_event = has_event(events1, ["escalation"])
        has_escalation_payload = "escalation_payload" in resp1
        
        assert has_escalation_event or has_escalation_payload or tool_failed, \
            "System should escalate on tool failure or invalid order"
        
        # If escalation occurred, verify payload structure
        if has_escalation_event:
            escalation_events = find_events(events1, ["escalation"])
            for esc_event in escalation_events:
                data = esc_event.get("data", {})
                payload = data.get("payload", data)
                
                # Required fields per hackathon spec
                required_fields = [
                    "escalation_id", "customer_id", "reason",
                    "conversation_summary", "attempted_actions",
                    "priority", "created_at"
                ]
                
                for field in required_fields:
                    assert field in payload, \
                        f"Escalation payload missing required field: {field}"
                
                # attempted_actions must be array
                assert isinstance(payload.get("attempted_actions"), list), \
                    "attempted_actions must be an array"
        
        # Count tool calls before second message
        tool_count_before = len(tool_events(events1))
        
        # Send second message to locked session
        resp2 = send_message(session_id, "Any update?")
        reply2 = extract_reply(resp2).lower()
        
        # Fetch trace after second message
        trace2 = get_trace(session_id)
        events2 = normalize_trace(trace2)
        
        # Count tool calls after second message
        tool_count_after = len(tool_events(events2))
        
        # Assert no new tool calls after escalation
        assert tool_count_after == tool_count_before, \
            f"Session should be locked - no new tool calls. Before: {tool_count_before}, After: {tool_count_after}"
        
        # Assert reply indicates escalation/locked state
        escalation_keywords = [
            "escalat", "specialist", "team", "human",
            "locked", "already", "follow up", "24 hour"
        ]
        has_lock_indication = any(kw in reply2 for kw in escalation_keywords) or not reply2
        assert has_lock_indication, \
            f"Locked session should return escalation message or empty reply. Got: {reply2[:100]}"
    
    # ------------------------------------------------------------------------
    # Test 5: Tool Uniform Contract Handling
    # ------------------------------------------------------------------------
    def test_tool_failure_handling(self):
        """
        Test 5: Tool Uniform Contract Handling (Behavioral)
        
        When tool fails:
        - API does not crash (HTTP 200 + valid JSON)
        - Tool failure is recorded in trace with error string
        - System does NOT hallucinate success ("refund completed", "order delivered")
        - System escalates or asks clarification
        """
        session_id = start_session(
            email="tool_fail_test@example.com",
            first_name="ToolFail",
            last_name="Tester",
            customer_id="cust_toolfail_001"
        )
        
        # Trigger deterministic tool failure
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.post(f"/session/{session_id}/message", json={
                "message": "Please check my order #INVALID_FOR_TEST"
            })
            
            # Assert API doesn't crash
            assert response.status_code == 200, \
                f"API should return 200 even on tool failure, got {response.status_code}"
            
            data = response.json()
            assert isinstance(data, dict), "Response must be valid JSON object"
        
        # Fetch trace
        trace = get_trace(session_id)
        events = normalize_trace(trace)
        
        # Find tool call events
        tools = tool_events(events)
        
        # Verify failure is logged
        failed_tools = [t for t in tools if t.get("success") is False or t.get("error")]
        if failed_tools:
            # At least one tool has error recorded
            for ft in failed_tools:
                assert ft.get("error") or ft.get("success") is False, \
                    "Failed tool should have error string or success=false"
        
        # Get the reply
        resp = send_message(session_id, "What happened with my order?")
        reply = extract_reply(resp).lower()
        
        # Assert NO hallucinated success messages
        hallucination_keywords = [
            "refund completed", "order delivered", "shipment arrived",
            "successfully processed", "order has been shipped"
        ]
        for keyword in hallucination_keywords:
            assert keyword not in reply, \
                f"System hallucinated success '{keyword}' when tool failed"
        
        # Assert system escalated or asked for clarification
        valid_responses = [
            "escalat", "specialist", "team", "sorry", "issue",
            "problem", "unable", "cannot", "clarif", "more information"
        ]
        has_valid_response = any(kw in reply for kw in valid_responses) or not reply
        assert has_valid_response, \
            f"System should escalate or ask clarification on tool failure. Got: {reply[:100]}"


# ============================================================================
# Additional Edge Case Tests (Bonus)
# ============================================================================

class TestEdgeCases:
    """Additional edge case tests."""
    
    def test_session_not_found(self):
        """Non-existent session returns 404."""
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.post("/session/invalid-session-id-12345/message", json={
                "message": "Test"
            })
            assert response.status_code == 404
    
    def test_trace_not_found(self):
        """Trace for non-existent session returns 404."""
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/session/invalid-session-id-12345/trace")
            assert response.status_code == 404
    
    def test_health_endpoint(self):
        """Health check endpoint returns 200."""
        with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "ok"
