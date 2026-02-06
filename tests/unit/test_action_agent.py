"""
Unit tests for ActionAgent.
Developer: Dev B
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from agents.action_agent import ActionAgent
from tools.client import ToolsClient, ToolCallResult
from schemas.workflow import WorkflowDecision, ToolPlan
from schemas.session import Session, CustomerInfo, CaseContext, Message


class TestActionAgent:
    """Test suite for ActionAgent."""
    
    @pytest.fixture
    def mock_tools_client(self):
        """Mock ToolsClient for testing."""
        client = Mock(spec=ToolsClient)
        return client
    
    @pytest.fixture
    def action_agent(self, mock_tools_client):
        """Create ActionAgent with mock client."""
        return ActionAgent(tools_client=mock_tools_client)
    
    @pytest.fixture
    def sample_session(self):
        """Create a sample session for testing."""
        return Session(
            session_id="test_session_123",
            customer_info=CustomerInfo(
                customer_id="cust_456",
                name="John Doe",
                email="john@example.com"
            ),
            case_context=CaseContext(
                order_id="ORD-12345",
                tracking_number="TRACK-789",
                item_name="Blue Widget",
                order_date="2026-01-15",
                shipping_status="in_transit"
            ),
            messages=[
                Message(role="customer", content="Where is my order?")
            ]
        )
    
    def test_execute_tool_success(self, action_agent, mock_tools_client, sample_session):
        """Test successful tool execution."""
        # Setup
        decision = WorkflowDecision(
            workflow_id="WISMO",
            next_action="call_tool",
            tool_plan=[
                ToolPlan(
                    tool_name="shopify_get_order_details",
                    params={"order_id": "{order_id}"}
                )
            ]
        )
        
        # Mock successful tool response
        mock_tools_client.execute.return_value = ToolCallResult(
            tool_name="shopify_get_order_details",
            params={"order_id": "ORD-12345"},
            success=True,
            data={"order_status": "shipped", "tracking": "TRACK-789"},
            error="",
            retry_count=0,
            should_escalate=False
        )
        
        # Execute
        result = action_agent.execute(sample_session, decision)
        
        # Assert
        assert result["success"] is True
        assert result["should_escalate"] is False
        assert len(result["results"]) == 1
        assert result["results"][0].tool_name == "shopify_get_order_details"
        
        # Verify tool was called with resolved params
        mock_tools_client.execute.assert_called_once_with(
            tool_name="shopify_get_order_details",
            params={"order_id": "ORD-12345"}
        )
        
        # Verify tool_history was updated
        assert len(sample_session.tool_history) == 1
        assert sample_session.tool_history[0]["tool_name"] == "shopify_get_order_details"
        assert sample_session.tool_history[0]["success"] is True
    
    def test_resolve_params_from_session(self, action_agent, sample_session):
        """Test parameter placeholder resolution from session context."""
        raw_params = {
            "order_id": "{order_id}",
            "customer_id": "{customer_id}",
            "tracking_number": "{tracking_number}",
            "item_name": "{item_name}",
            "literal_value": "some_literal"
        }
        
        resolved = action_agent._resolve_params(raw_params, sample_session)
        
        assert resolved["order_id"] == "ORD-12345"
        assert resolved["customer_id"] == "cust_456"
        assert resolved["tracking_number"] == "TRACK-789"
        assert resolved["item_name"] == "Blue Widget"
        assert resolved["literal_value"] == "some_literal"
    
    def test_resolve_params_missing_context(self, action_agent, sample_session):
        """Test parameter resolution when context value is missing."""
        # Clear refund_reason (not set in fixture)
        raw_params = {
            "order_id": "{order_id}",
            "refund_reason": "{refund_reason}",  # This is None in session
            "literal": "test"
        }
        
        resolved = action_agent._resolve_params(raw_params, sample_session)
        
        assert resolved["order_id"] == "ORD-12345"
        # Should keep placeholder if value not available
        assert resolved["refund_reason"] == "{refund_reason}"
        assert resolved["literal"] == "test"
    
    def test_tool_failure_sets_escalation(self, action_agent, mock_tools_client, sample_session):
        """Test that tool failure with should_escalate=True triggers escalation."""
        decision = WorkflowDecision(
            workflow_id="WISMO",
            next_action="call_tool",
            tool_plan=[
                ToolPlan(
                    tool_name="shopify_get_order_details",
                    params={"order_id": "{order_id}"}
                )
            ]
        )
        
        # Mock failed tool with escalation flag
        mock_tools_client.execute.return_value = ToolCallResult(
            tool_name="shopify_get_order_details",
            params={"order_id": "ORD-12345"},
            success=False,
            data={},
            error="API timeout after 2 retries",
            retry_count=2,
            should_escalate=True
        )
        
        result = action_agent.execute(sample_session, decision)
        
        assert result["success"] is False
        assert result["should_escalate"] is True
        assert result["error"] == "API timeout after 2 retries"
        assert len(result["results"]) == 1
    
    def test_result_stored_in_tool_history(self, action_agent, mock_tools_client, sample_session):
        """Test that tool results are stored in session.tool_history."""
        decision = WorkflowDecision(
            workflow_id="REFUND_STANDARD",
            next_action="call_tool",
            tool_plan=[
                ToolPlan(
                    tool_name="shopify_refund_order",
                    params={"order_id": "{order_id}", "amount": 50.00}
                )
            ]
        )
        
        mock_tools_client.execute.return_value = ToolCallResult(
            tool_name="shopify_refund_order",
            params={"order_id": "ORD-12345", "amount": 50.00},
            success=True,
            data={"refund_id": "REF-999"},
            timestamp="2026-02-06T18:30:00"
        )
        
        # Initially empty
        assert len(sample_session.tool_history) == 0
        
        result = action_agent.execute(sample_session, decision)
        
        # Should be stored
        assert len(sample_session.tool_history) == 1
        tool_record = sample_session.tool_history[0]
        
        assert tool_record["tool_name"] == "shopify_refund_order"
        assert tool_record["params"]["order_id"] == "ORD-12345"
        assert tool_record["params"]["amount"] == 50.00
        assert tool_record["success"] is True
        assert tool_record["data"]["refund_id"] == "REF-999"
    
    def test_multiple_tools_in_plan(self, action_agent, mock_tools_client, sample_session):
        """Test executing multiple tools in sequence."""
        decision = WorkflowDecision(
            workflow_id="WRONG_MISSING",
            next_action="call_tool",
            tool_plan=[
                ToolPlan(
                    tool_name="shopify_create_return",
                    params={"order_id": "{order_id}"}
                ),
                ToolPlan(
                    tool_name="shopify_create_store_credit",
                    params={"customer_id": "{customer_id}", "amount": 25.00}
                )
            ]
        )
        
        # Mock responses for both tools
        mock_tools_client.execute.side_effect = [
            ToolCallResult(
                tool_name="shopify_create_return",
                params={"order_id": "ORD-12345"},
                success=True,
                data={"return_id": "RET-111"}
            ),
            ToolCallResult(
                tool_name="shopify_create_store_credit",
                params={"customer_id": "cust_456", "amount": 25.00},
                success=True,
                data={"credit_id": "CREDIT-222"}
            )
        ]
        
        result = action_agent.execute(sample_session, decision)
        
        assert result["success"] is True
        assert len(result["results"]) == 2
        assert result["results"][0].tool_name == "shopify_create_return"
        assert result["results"][1].tool_name == "shopify_create_store_credit"
        
        # Both should be in tool_history
        assert len(sample_session.tool_history) == 2
    
    def test_stops_on_escalation(self, action_agent, mock_tools_client, sample_session):
        """Test that tool execution stops when escalation is triggered."""
        decision = WorkflowDecision(
            workflow_id="TEST",
            next_action="call_tool",
            tool_plan=[
                ToolPlan(tool_name="tool_1", params={}),
                ToolPlan(tool_name="tool_2", params={}),
                ToolPlan(tool_name="tool_3", params={})
            ]
        )
        
        # First tool fails with escalation
        mock_tools_client.execute.return_value = ToolCallResult(
            tool_name="tool_1",
            params={},
            success=False,
            data={},
            error="Critical failure",
            should_escalate=True
        )
        
        result = action_agent.execute(sample_session, decision)
        
        # Should stop after first failure
        assert len(result["results"]) == 1
        assert result["should_escalate"] is True
        assert mock_tools_client.execute.call_count == 1
    
    def test_invalid_next_action(self, action_agent, sample_session):
        """Test handling of invalid next_action."""
        decision = WorkflowDecision(
            workflow_id="TEST",
            next_action="respond",  # Not 'call_tool'
            tool_plan=[]
        )
        
        result = action_agent.execute(sample_session, decision)
        
        assert result["success"] is False
        assert "Invalid action" in result["error"]
        assert result["should_escalate"] is False
    
    def test_empty_tool_plan(self, action_agent, sample_session):
        """Test handling of empty tool plan."""
        decision = WorkflowDecision(
            workflow_id="TEST",
            next_action="call_tool",
            tool_plan=[]  # Empty
        )
        
        result = action_agent.execute(sample_session, decision)
        
        assert result["success"] is False
        assert "No tools specified" in result["error"]
    
    def test_to_trace_event(self, action_agent):
        """Test trace event generation."""
        results = [
            ToolCallResult(
                tool_name="tool_1",
                params={"key": "value"},
                success=True,
                data={"result": "ok"},
                retry_count=0,
                should_escalate=False
            ),
            ToolCallResult(
                tool_name="tool_2",
                params={},
                success=False,
                data={},
                error="Failed",
                retry_count=1,
                should_escalate=True
            )
        ]
        
        trace_event = action_agent.to_trace_event(results)
        
        assert trace_event.agent == "action"
        assert trace_event.action == "execute_tools"
        assert trace_event.data["total_calls"] == 2
        assert trace_event.data["success_count"] == 1
        assert trace_event.data["escalation_triggered"] is True
        assert len(trace_event.data["tools_executed"]) == 2
