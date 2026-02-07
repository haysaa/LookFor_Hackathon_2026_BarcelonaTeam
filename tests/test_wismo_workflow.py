"""
Tests for WISMO workflow with day-based promise logic.
Tests the complete workflow including order lookup, status detection, promise rules.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.models import (
    Session, SessionStatus, CustomerInfo, CaseContext, 
    Message, MessageRole, Intent
)
from app.wismo_helpers import (
    get_contact_day, compute_promise_deadline, 
    is_promise_deadline_passed, normalize_shipping_status
)
from app.workflow_engine import WorkflowEngine
from app.store import session_store


# ================ Unit Tests for wismo_helpers ================

class TestGetContactDay:
    """Tests for get_contact_day function."""
    
    def test_returns_cached_contact_day(self):
        """Should return cached contact_day if already set."""
        session = MagicMock()
        session.case_context.contact_day = "Tue"
        session.messages = []
        
        result = get_contact_day(session)
        assert result == "Tue"
    
    def test_computes_from_customer_message(self):
        """Should compute from first customer message timestamp."""
        # Create a Monday timestamp
        monday = datetime(2026, 2, 2, 10, 0, 0)  # 2026-02-02 is a Monday
        
        session = MagicMock()
        session.case_context.contact_day = None
        
        msg = MagicMock()
        msg.role.value = "customer"
        msg.timestamp = monday
        session.messages = [msg]
        
        result = get_contact_day(session)
        assert result == "Mon"
    
    def test_fallback_to_session_creation(self):
        """Should fallback to session created_at if no messages."""
        friday = datetime(2026, 2, 6, 10, 0, 0)  # 2026-02-06 is a Friday
        
        session = MagicMock()
        session.case_context.contact_day = None
        session.messages = []
        session.created_at = friday
        
        result = get_contact_day(session)
        assert result == "Fri"


class TestComputePromiseDeadline:
    """Tests for compute_promise_deadline function."""
    
    def test_monday_returns_friday(self):
        """Monday contact should promise Friday."""
        reference = datetime(2026, 2, 2)  # Monday
        promise_type, deadline = compute_promise_deadline("Mon", reference)
        
        assert promise_type == "FRIDAY"
        assert deadline == "2026-02-06"  # That Friday
    
    def test_wednesday_returns_friday(self):
        """Wednesday contact should promise Friday."""
        reference = datetime(2026, 2, 4)  # Wednesday
        promise_type, deadline = compute_promise_deadline("Wed", reference)
        
        assert promise_type == "FRIDAY"
        assert deadline == "2026-02-06"  # That Friday
    
    def test_thursday_returns_next_monday(self):
        """Thursday contact should promise early next week (Monday)."""
        reference = datetime(2026, 2, 5)  # Thursday
        promise_type, deadline = compute_promise_deadline("Thu", reference)
        
        assert promise_type == "EARLY_NEXT_WEEK"
        assert deadline == "2026-02-09"  # Next Monday
    
    def test_sunday_returns_next_monday(self):
        """Sunday contact should promise early next week (Monday)."""
        reference = datetime(2026, 2, 8)  # Sunday
        promise_type, deadline = compute_promise_deadline("Sun", reference)
        
        assert promise_type == "EARLY_NEXT_WEEK"
        assert deadline == "2026-02-09"  # Next Monday
    
    def test_invalid_day_defaults_to_next_week(self):
        """Invalid day should default to EARLY_NEXT_WEEK."""
        reference = datetime(2026, 2, 2)  # Monday
        promise_type, deadline = compute_promise_deadline("Invalid", reference)
        
        assert promise_type == "EARLY_NEXT_WEEK"


class TestIsPromiseDeadlinePassed:
    """Tests for is_promise_deadline_passed function."""
    
    def test_not_passed_if_before(self):
        """Should return False if before deadline."""
        deadline = "2026-02-06"
        check_date = datetime(2026, 2, 5)
        
        assert is_promise_deadline_passed(deadline, check_date) is False
    
    def test_not_passed_on_deadline_day(self):
        """Should return False on the deadline day itself."""
        deadline = "2026-02-06"
        check_date = datetime(2026, 2, 6, 23, 59)
        
        assert is_promise_deadline_passed(deadline, check_date) is False
    
    def test_passed_if_after(self):
        """Should return True if after deadline."""
        deadline = "2026-02-06"
        check_date = datetime(2026, 2, 7, 0, 1)
        
        assert is_promise_deadline_passed(deadline, check_date) is True
    
    def test_empty_deadline_returns_false(self):
        """Should return False if deadline is empty."""
        assert is_promise_deadline_passed("", None) is False
        assert is_promise_deadline_passed(None, None) is False


class TestNormalizeShippingStatus:
    """Tests for normalize_shipping_status function."""
    
    def test_delivered_variants(self):
        """Should normalize delivered variants."""
        assert normalize_shipping_status("delivered") == "delivered"
        assert normalize_shipping_status("DELIVERED") == "delivered"
        assert normalize_shipping_status("complete") == "delivered"
    
    def test_unfulfilled_variants(self):
        """Should normalize unfulfilled variants."""
        assert normalize_shipping_status("unfulfilled") == "unfulfilled"
        assert normalize_shipping_status("pending") == "unfulfilled"
        assert normalize_shipping_status("processing") == "unfulfilled"
    
    def test_in_transit_variants(self):
        """Should normalize in_transit variants."""
        assert normalize_shipping_status("shipped") == "in_transit"
        assert normalize_shipping_status("fulfilled") == "in_transit"
        assert normalize_shipping_status("in_transit") == "in_transit"
        assert normalize_shipping_status("out_for_delivery") == "in_transit"
    
    def test_unknown_returns_unknown(self):
        """Should return unknown for unrecognized status."""
        assert normalize_shipping_status("some_weird_status") == "unknown"
        assert normalize_shipping_status("") == "unknown"
        assert normalize_shipping_status(None) == "unknown"


# ================ Integration Tests for WISMO Workflow ================

@pytest.fixture
def wismo_engine():
    """Create workflow engine with WISMO workflow loaded."""
    return WorkflowEngine()


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    customer = CustomerInfo(
        customer_email="test@example.com",
        first_name="John",
        last_name="Doe",
        shopify_customer_id="cust_123"
    )
    session = Session(customer_info=customer)
    session.intent = Intent.WISMO
    return session


class TestWismoWorkflowRules:
    """Integration tests for WISMO workflow rule evaluation."""
    
    def test_no_order_fetches_orders(self, wismo_engine, sample_session):
        """When no order_id and orders not fetched, should call tool."""
        # No order info yet
        sample_session.case_context.order_id = None
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["fetch_customer_orders"]
    
    def test_orders_fetched_but_no_order_asks_clarifying(self, wismo_engine, sample_session):
        """When orders fetched but no order found, should ask for order ID."""
        sample_session.case_context.order_id = None
        sample_session.case_context.extra["orders_fetched"] = True
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert decision["policy_applied"] == ["require_order_id"]
        assert len(decision["clarifying_questions"]) > 0
    
    def test_has_order_but_no_status_fetches_details(self, wismo_engine, sample_session):
        """When we have order_id but no status, should fetch details."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = None
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["fetch_order_status"]
        assert decision["tool_plan"][0]["tool_name"] == "shopify_get_order_details"
    
    def test_unfulfilled_responds_not_shipped(self, wismo_engine, sample_session):
        """When status is unfulfilled, should say not shipped yet."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "unfulfilled"
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["order_not_shipped"]
        assert "hasn't shipped yet" in decision["response_template"]
    
    def test_delivered_responds_delivered(self, wismo_engine, sample_session):
        """When status is delivered, should say delivered."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "delivered"
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["order_delivered"]
        assert "delivered" in decision["response_template"].lower()
    
    def test_mon_wed_in_transit_friday_promise(self, wismo_engine, sample_session):
        """Mon-Wed contact + in_transit = Friday promise."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "in_transit"
        sample_session.case_context.contact_day = "Mon"
        sample_session.case_context.wismo_promise_type = None
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["friday_promise"]
        assert "Friday" in decision["response_template"]
        assert decision["set_context"]["wismo_promise_type"] == "FRIDAY"
    
    def test_thu_sun_in_transit_next_week_promise(self, wismo_engine, sample_session):
        """Thu-Sun contact + in_transit = next week promise."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "in_transit"
        sample_session.case_context.contact_day = "Fri"
        sample_session.case_context.wismo_promise_type = None
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["next_week_promise"]
        assert "next week" in decision["response_template"]
        assert decision["set_context"]["wismo_promise_type"] == "EARLY_NEXT_WEEK"
    
    def test_tracking_available_returns_link(self, wismo_engine, sample_session):
        """When tracking requested and available, should return link."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "in_transit"
        sample_session.case_context.tracking_url = "https://track.example.com/12345"
        sample_session.case_context.extra["tracking_requested"] = True
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["provide_tracking"]
        assert "track" in decision["response_template"].lower()
    
    def test_tracking_not_available_says_not_ready(self, wismo_engine, sample_session):
        """When tracking requested but not available, should say not ready."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "in_transit"
        sample_session.case_context.tracking_url = None
        sample_session.case_context.extra["tracking_requested"] = True
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["tracking_not_ready"]
    
    def test_post_promise_deadline_passed_escalates(self, wismo_engine, sample_session):
        """When promise deadline passed and still not delivered, should escalate."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "in_transit"
        sample_session.case_context.wismo_promise_type = "FRIDAY"
        sample_session.case_context.wismo_promise_deadline = "2026-02-01"  # Past date
        
        # Manually set the context to simulate deadline passed
        # The _build_context will compute wismo_promise_deadline_passed
        # Since the deadline is in the past, it should trigger escalation
        decision = wismo_engine.evaluate(sample_session)
        
        # Should escalate because deadline has passed
        assert decision["next_action"] == "escalate"
        assert "promise" in decision["escalation_reason"].lower()
    
    def test_unknown_status_escalates(self, wismo_engine, sample_session):
        """When status is unknown, should escalate."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "unknown"
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "escalate"
        assert decision["policy_applied"] == ["status_unclear"]


# ================ Escalation Payload Tests ================

class TestWismoEscalation:
    """Tests for WISMO escalation payload structure."""
    
    def test_escalation_has_required_fields(self, wismo_engine, sample_session):
        """Escalation decision should have all required fields."""
        sample_session.case_context.order_id = "ORD-12345"
        sample_session.case_context.shipping_status = "unknown"
        
        decision = wismo_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "escalate"
        assert "escalation_reason" in decision
        assert decision["escalation_reason"] is not None
        # Priority should be present
        assert "escalation_priority" in decision


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
