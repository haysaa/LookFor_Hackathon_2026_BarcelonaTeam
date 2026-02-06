"""
Unit Tests - ToolsClient
Version: 1.0
Developer: Dev B

Tests ToolsClient retry logic, response normalization, and escalation flagging.
"""
import pytest
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.client import ToolsClient, ToolCallResult
from tools.mock_server import MockToolServer


class TestToolCallResult:
    """Test ToolCallResult dataclass."""
    
    def test_success_result(self):
        """Test creating a successful result."""
        result = ToolCallResult(
            tool_name="check_order_status",
            params={"order_id": "12345"},
            success=True,
            data={"status": "shipped"},
            retry_count=0
        )
        
        assert result.success is True
        assert result.should_escalate is False
        assert result.retry_count == 0
    
    def test_failed_result_with_escalation(self):
        """Test failed result sets escalation flag."""
        result = ToolCallResult(
            tool_name="check_order_status",
            params={"order_id": "12345"},
            success=False,
            data={},
            error="API timeout",
            retry_count=1,
            should_escalate=True
        )
        
        assert result.success is False
        assert result.should_escalate is True


class TestMockToolServer:
    """Test MockToolServer responses."""
    
    def test_check_order_status_known_order(self):
        """Test checking status of known order."""
        server = MockToolServer()
        result = server.execute("check_order_status", {"order_id": "12345"})
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["order_id"] == "12345"
        assert result["data"]["status"] in ["pending", "processing", "shipped", "delivered", "cancelled"]
    
    def test_check_order_status_unknown_order(self):
        """Test checking status of unknown order returns mock data."""
        server = MockToolServer()
        result = server.execute("check_order_status", {"order_id": "UNKNOWN123"})
        
        assert result["success"] is True
        assert result["data"]["order_id"] == "UNKNOWN123"
    
    def test_issue_store_credit(self):
        """Test issuing store credit with bonus."""
        server = MockToolServer()
        result = server.execute("issue_store_credit", {
            "customer_id": "cust_123",
            "amount": 100.00,
            "bonus_percent": 10,
            "reason": "Test"
        })
        
        assert result["success"] is True
        assert result["data"]["total_amount"] == 110.00  # 100 + 10%
    
    def test_request_reship_requires_approval(self):
        """Test reship always requires manual approval."""
        server = MockToolServer()
        result = server.execute("request_reship", {
            "order_id": "12345",
            "reason": "Missing item"
        })
        
        assert result["success"] is True
        assert result["data"]["status"] == "pending_approval"
        assert result["data"]["requires_manual_review"] is True
    
    def test_simulated_failure(self):
        """Test simulated failure with high fail rate."""
        server = MockToolServer(fail_rate=1.0)  # 100% fail
        result = server.execute("check_order_status", {"order_id": "12345"})
        
        assert result["success"] is False
        assert "error" in result


class TestToolsClient:
    """Test ToolsClient wrapper functionality."""
    
    def test_successful_execution(self):
        """Test successful tool execution."""
        client = ToolsClient(use_mock=True)
        result = client.execute("check_order_status", {"order_id": "12345"})
        
        assert result.success is True
        assert result.should_escalate is False
        assert "status" in result.data
    
    def test_unknown_tool_escalates(self):
        """Test unknown tool sets escalation flag."""
        client = ToolsClient(use_mock=True)
        result = client.execute("nonexistent_tool", {})
        
        assert result.success is False
        assert result.should_escalate is True
        assert "not found" in result.error.lower()
    
    def test_retry_on_failure(self):
        """Test retry logic on transient failure."""
        # Create client with mock that fails 50% of time
        client = ToolsClient(use_mock=True, max_retries=2, mock_fail_rate=0.5)
        
        # Run multiple times to test retry behavior
        successes = 0
        for _ in range(10):
            client.clear_history()
            result = client.execute("check_order_status", {"order_id": "12345"})
            if result.success:
                successes += 1
        
        # With retries, most should succeed
        assert successes >= 5
    
    def test_execute_plan(self):
        """Test executing a tool plan."""
        client = ToolsClient(use_mock=True)
        plan = [
            {"tool_name": "check_order_status", "params": {"order_id": "12345"}},
            {"tool_name": "get_shipping_info", "params": {"tracking_number": "TRK123"}}
        ]
        
        results = client.execute_plan(plan)
        
        assert len(results) == 2
        assert all(r.success for r in results)
    
    def test_trace_events(self):
        """Test trace event generation."""
        client = ToolsClient(use_mock=True)
        client.execute("check_order_status", {"order_id": "12345"})
        
        events = client.to_trace_events()
        
        assert len(events) == 1
        assert events[0]["agent"] == "tools_client"
        assert events[0]["action"] == "tool_call"
        assert events[0]["data"]["tool_name"] == "check_order_status"
    
    def test_any_escalation_needed(self):
        """Test escalation check across all calls."""
        client = ToolsClient(use_mock=True)
        
        # Successful call
        client.execute("check_order_status", {"order_id": "12345"})
        assert client.any_escalation_needed() is False
        
        # Failed call
        client.execute("nonexistent_tool", {})
        assert client.any_escalation_needed() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
