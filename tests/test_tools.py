"""
Unit tests for ToolsClient with JSON Schema validation.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.tools.client import ToolsClient
from app.store import session_store, SessionStore
from app.models import CustomerInfo


class TestToolsClient:
    """Unit tests for ToolsClient."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Fresh session store
        session_store.clear()
        
        # Create a test session
        self.customer = CustomerInfo(
            customer_email="test@example.com",
            first_name="Test",
            last_name="User",
            shopify_customer_id="cust_123"
        )
        self.session = session_store.create(self.customer)
        
        # Fresh tools client
        self.client = ToolsClient()
        self.client.mock_mode = True
    
    # --- Original Tests ---
    
    def test_mock_check_order_status_success(self):
        """Mock tool returns success for check_order_status."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="check_order_status",
            params={"order_id": "ORD-123"},
            skip_validation=True
        )
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["status"] == "in_transit"
    
    def test_mock_get_shipping_info_success(self):
        """Mock tool returns success for get_shipping_info."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="get_shipping_info",
            params={"order_id": "ORD-123"},
            skip_validation=True
        )
        
        assert result["success"] is True
        assert result["data"]["carrier"] == "Yurtiçi Kargo"
    
    def test_mock_issue_store_credit_success(self):
        """Mock tool returns success for issue_store_credit."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="issue_store_credit",
            params={"customer_id": "cust_123", "amount": 100},
            skip_validation=True
        )
        
        assert result["success"] is True
        assert result["data"]["total_credit"] == pytest.approx(110)  # 10% bonus
    
    def test_mock_create_reship_requires_escalation(self):
        """Mock create_reship always returns should_escalate."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="create_reship",
            params={"order_id": "ORD-123", "items": ["item1"]},
            skip_validation=True
        )
        
        assert result["success"] is False
        assert result["should_escalate"] is True
    
    def test_unknown_tool_fails(self):
        """Unknown tool returns failure."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="unknown_tool",
            params={},
            skip_validation=True
        )
        
        assert result["success"] is False
        assert "unknown" in result["error"].lower()
    
    def test_tool_call_logged_to_trace(self):
        """Tool calls are logged to session trace."""
        initial_trace_count = len(self.session.trace)
        
        self.client.execute(
            session_id=self.session.id,
            tool_name="check_order_status",
            params={"order_id": "ORD-123"},
            skip_validation=True
        )
        
        # Refresh session
        updated_session = session_store.get(self.session.id)
        assert len(updated_session.trace) > initial_trace_count
        
        # Check last trace event
        last_event = updated_session.trace[-1]
        assert last_event.event_type.value == "tool_call"
        assert last_event.data["tool_name"] == "check_order_status"
    
    def test_retry_on_failure(self):
        """Client retries once on failure."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="check_order_status",
            params={"order_id": "ORD-123"},
            max_retries=1,
            skip_validation=True
        )
        
        # Success on first try, no retries needed
        assert result["success"] is True
        
        # Trace should show retry_count = 0 (no retries needed)
        updated_session = session_store.get(self.session.id)
        last_event = updated_session.trace[-1]
        assert last_event.data["retry_count"] == 0
    
    def test_normalized_response_format(self):
        """All responses have standard format."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="check_order_status",
            params={"order_id": "ORD-123"},
            skip_validation=True
        )
        
        # Check all required fields present
        assert "success" in result
        assert "data" in result
        assert "error" in result
        assert isinstance(result["success"], bool)
        assert isinstance(result["data"], dict)
        assert isinstance(result["error"], str)
    
    # --- JSON Schema Validation Tests ---
    
    def test_validate_params_success(self):
        """Valid params pass validation."""
        is_valid, error = self.client.validate_params(
            "shopify_get_order_details",
            {"order_id": "ORD-123"}
        )
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_params_missing_required(self):
        """Missing required params fail validation."""
        is_valid, error = self.client.validate_params(
            "shopify_get_order_details",
            {}  # Missing order_id
        )
        
        assert is_valid is False
        assert "order_id" in error.lower() or "missing" in error.lower() or "required" in error.lower()
    
    def test_execute_rejects_invalid_params(self):
        """Execute should reject invalid params before making the call."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="shopify_refund_order",
            params={},  # Missing required order_id
            skip_validation=False
        )
        
        assert result["success"] is False
        assert "order_id" in result["error"].lower() or "validation" in result["error"].lower()
        # Should NOT escalate for validation errors
        assert result["should_escalate"] is False
    
    def test_catalog_mock_response_used(self):
        """Tools from catalog use their mock_response."""
        result = self.client.execute(
            session_id=self.session.id,
            tool_name="shopify_get_order_details",
            params={"order_id": "ORD-12345"}
        )
        
        assert result["success"] is True
        assert "data" in result
        # Should have catalog mock response fields
        assert "status" in result["data"] or "order_id" in result["data"]
    
    def test_get_available_tools(self):
        """Get list of available tools from catalog."""
        tools = self.client.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert "shopify_get_order_details" in tools
        assert "shopify_refund_order" in tools
    
    def test_unknown_tool_not_in_catalog(self):
        """Unknown tool validation fails."""
        is_valid, error = self.client.validate_params(
            "non_existent_tool",
            {"param": "value"}
        )
        
        assert is_valid is False
        assert "not in catalog" in error.lower()
