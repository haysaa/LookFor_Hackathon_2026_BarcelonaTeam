"""
Tests for REFUND_STANDARD workflow.
Covers all required test cases from spec.
"""
import pytest
from datetime import datetime, timedelta

from app.models import Session, CustomerInfo, CaseContext, Intent
from app.refund_helpers import (
    compute_shipping_promise, get_usage_tip, detect_refund_reason,
    detect_expectation_cause, detect_wait_acceptance, detect_resolution_choice,
    is_shipping_promise_passed
)
from app.workflow_engine import WorkflowEngine


# ================ Unit Tests for refund_helpers ================

class TestComputeShippingPromise:
    """Tests for compute_shipping_promise function."""
    
    def test_monday_returns_friday(self):
        """Mon contact -> Friday promise."""
        promise_type, deadline = compute_shipping_promise("Mon")
        assert promise_type == "FRIDAY"
    
    def test_tuesday_returns_friday(self):
        """Tue contact -> Friday promise."""
        promise_type, deadline = compute_shipping_promise("Tue")
        assert promise_type == "FRIDAY"
    
    def test_wednesday_returns_next_week(self):
        """Wed contact -> early next week promise."""
        promise_type, deadline = compute_shipping_promise("Wed")
        assert promise_type == "EARLY_NEXT_WEEK"
    
    def test_friday_returns_next_week(self):
        """Fri contact -> early next week promise."""
        promise_type, deadline = compute_shipping_promise("Fri")
        assert promise_type == "EARLY_NEXT_WEEK"


class TestGetUsageTip:
    """Tests for get_usage_tip function."""
    
    def test_falling_asleep_tip(self):
        """Should return tip for falling asleep."""
        tip = get_usage_tip("falling_asleep")
        assert tip is not None
        assert "30-60 minutes" in tip
    
    def test_taste_tip(self):
        """Should return tip for taste."""
        tip = get_usage_tip("taste")
        assert tip is not None
        assert "juice" in tip or "smoothie" in tip
    
    def test_unknown_cause(self):
        """Should return None for unknown cause."""
        assert get_usage_tip("unknown") is None


class TestDetectRefundReason:
    """Tests for detect_refund_reason function."""
    
    def test_detects_damaged(self):
        """Should detect damaged/wrong."""
        assert detect_refund_reason("The item is damaged") == "DAMAGED_OR_WRONG"
        assert detect_refund_reason("I got the wrong item") == "DAMAGED_OR_WRONG"
    
    def test_detects_shipping_delay(self):
        """Should detect shipping delay."""
        assert detect_refund_reason("There's a shipping delay") == "SHIPPING_DELAY"
        assert detect_refund_reason("My order still hasn't arrived") == "SHIPPING_DELAY"
    
    def test_detects_changed_mind(self):
        """Should detect changed mind."""
        assert detect_refund_reason("I changed my mind") == "CHANGED_MIND"
        assert detect_refund_reason("I don't want it anymore") == "CHANGED_MIND"
    
    def test_detects_expectations(self):
        """Should detect expectations."""
        assert detect_refund_reason("Product didn't work for me") == "EXPECTATIONS"
        assert detect_refund_reason("It's not effective for me") == "EXPECTATIONS"


class TestDetectWaitAcceptance:
    """Tests for detect_wait_acceptance function."""
    
    def test_detects_acceptance(self):
        """Should detect acceptance."""
        assert detect_wait_acceptance("Yes, I can wait") == "ACCEPTED"
        assert detect_wait_acceptance("Ok, that's fine") == "ACCEPTED"
    
    def test_detects_decline(self):
        """Should detect decline."""
        assert detect_wait_acceptance("No, I can't wait") == "DECLINED"
        assert detect_wait_acceptance("I need it now") == "DECLINED"


class TestIsShippingPromisePassed:
    """Tests for is_shipping_promise_passed function."""
    
    def test_past_date_returns_true(self):
        """Past date should return True."""
        past = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        assert is_shipping_promise_passed(past) is True
    
    def test_future_date_returns_false(self):
        """Future date should return False."""
        future = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        assert is_shipping_promise_passed(future) is False


# ================ Integration Tests for Refund Workflow ================

@pytest.fixture
def refund_engine():
    """Create workflow engine."""
    return WorkflowEngine()


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    customer = CustomerInfo(
        customer_email="test@example.com",
        first_name="John",
        last_name="Doe",
        shopify_customer_id="cust_789"
    )
    session = Session(customer_info=customer)
    session.intent = Intent.REFUND_STANDARD
    return session


class TestRefundWorkflowRules:
    """Integration tests for Refund workflow rules."""
    
    def test_no_order_fetches_orders(self, refund_engine, sample_session):
        """Test: No order -> fetch customer orders."""
        sample_session.case_context.order_id = None
        sample_session.case_context.extra['orders_fetched'] = False
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["fetch_customer_orders"]
    
    def test_orders_fetched_asks_for_order_number(self, refund_engine, sample_session):
        """Test: Orders fetched but no match -> asks for order number."""
        sample_session.case_context.order_id = None
        sample_session.case_context.extra['orders_fetched'] = True
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert decision["policy_applied"] == ["require_order_id"]
    
    def test_missing_reason_asks_for_reason(self, refund_engine, sample_session):
        """Test: Missing refund_reason -> asks for reason selection."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = None
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert decision["policy_applied"] == ["collect_refund_reason"]
        assert "1." in decision["clarifying_questions"][0]
        assert "Product didn't meet expectations" in decision["clarifying_questions"][0]
    
    def test_expectations_asks_cause(self, refund_engine, sample_session):
        """Test: EXPECTATIONS -> asks one cause question."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "EXPECTATIONS"
        sample_session.case_context.expectation_cause = None
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert decision["policy_applied"] == ["expectations_identify_cause"]
        assert "falling asleep" in decision["clarifying_questions"][0].lower()
    
    def test_expectations_sends_tip(self, refund_engine, sample_session):
        """Test: EXPECTATIONS with cause -> sends usage tip."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "EXPECTATIONS"
        sample_session.case_context.expectation_cause = "falling_asleep"
        sample_session.case_context.usage_tip_sent = False
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["expectations_usage_tip"]
    
    def test_expectations_offers_swap(self, refund_engine, sample_session):
        """Test: EXPECTATIONS after tip -> offers swap."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "EXPECTATIONS"
        sample_session.case_context.expectation_cause = "taste"
        sample_session.case_context.usage_tip_sent = True
        sample_session.case_context.swap_offered = False
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["expectations_offer_swap"]
        assert "swap" in decision["response_template"].lower()
    
    def test_expectations_offers_store_credit(self, refund_engine, sample_session):
        """Test: EXPECTATIONS after swap declined -> store credit option."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "EXPECTATIONS"
        sample_session.case_context.expectation_cause = "no_effect"
        sample_session.case_context.usage_tip_sent = True
        sample_session.case_context.swap_offered = True
        sample_session.case_context.customer_resolution_choice = "REFUND"
        sample_session.case_context.refund_store_credit_offered = False
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["expectations_offer_store_credit"]
        assert "10%" in decision["response_template"]
    
    def test_shipping_delay_mon_tue_friday_promise(self, refund_engine, sample_session):
        """Test: SHIPPING_DELAY Mon/Tue -> wait until Friday asked."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "SHIPPING_DELAY"
        sample_session.case_context.contact_day = "Mon"
        sample_session.case_context.refund_shipping_wait_asked = False
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["shipping_delay_friday_promise"]
        assert "Friday" in decision["response_template"]
    
    def test_shipping_delay_wed_fri_next_week_promise(self, refund_engine, sample_session):
        """Test: SHIPPING_DELAY Wed-Fri -> wait until early next week asked."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "SHIPPING_DELAY"
        sample_session.case_context.contact_day = "Thu"
        sample_session.case_context.refund_shipping_wait_asked = False
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["shipping_delay_next_week_promise"]
        assert "early next week" in decision["response_template"].lower()
    
    def test_shipping_delay_decline_escalates_with_monica(self, refund_engine, sample_session):
        """Test: SHIPPING_DELAY decline wait -> escalates + Monica message + locks session."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "SHIPPING_DELAY"
        sample_session.case_context.contact_day = "Mon"
        sample_session.case_context.refund_shipping_wait_asked = True
        sample_session.case_context.customer_wait_acceptance = "DECLINED"
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "escalate"
        assert decision["policy_applied"] == ["shipping_delay_escalate"]
        # Check Monica message exists in response_template
        template = decision.get("response_template", "")
        assert template is not None and "Monica" in template
        assert "Refund, Escalated Shipping Delay" in decision["add_tags"]
    
    def test_damaged_wrong_replacement_escalates(self, refund_engine, sample_session):
        """Test: DAMAGED_OR_WRONG replacement chosen -> escalates + locks."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "DAMAGED_OR_WRONG"
        sample_session.case_context.replacement_offered = True
        sample_session.case_context.customer_resolution_choice = "REPLACEMENT"
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "escalate"
        assert decision["policy_applied"] == ["damaged_wrong_replacement_escalate"]
        assert "Refund, Escalated Replacement Review" in decision["add_tags"]
    
    def test_damaged_wrong_store_credit_calls_tool(self, refund_engine, sample_session):
        """Test: DAMAGED_OR_WRONG store credit chosen -> tool called + tag."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "DAMAGED_OR_WRONG"
        sample_session.case_context.replacement_offered = True
        sample_session.case_context.customer_resolution_choice = "STORE_CREDIT"
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["damaged_wrong_issue_store_credit"]
        assert decision["tool_plan"][0]["tool_name"] == "shopify_create_store_credit"
    
    def test_changed_mind_unfulfilled_cancels(self, refund_engine, sample_session):
        """Test: CHANGED_MIND unfulfilled -> cancel order tool called + tag."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "UNFULFILLED"
        sample_session.case_context.refund_reason = "CHANGED_MIND"
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["changed_mind_cancel_order"]
        assert decision["tool_plan"][0]["tool_name"] == "shopify_cancel_order"
        # Second tool should be shopify_add_tags
        assert decision["tool_plan"][1]["tool_name"] == "shopify_add_tags"
    
    def test_changed_mind_fulfilled_offers_credit(self, refund_engine, sample_session):
        """Test: CHANGED_MIND fulfilled -> store credit offer."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "CHANGED_MIND"
        sample_session.case_context.refund_store_credit_offered = False
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["changed_mind_offer_store_credit"]
        assert "10%" in decision["response_template"]
    
    def test_changed_mind_cash_refund(self, refund_engine, sample_session):
        """Test: CHANGED_MIND fulfilled declines credit -> cash refund."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "FULFILLED"
        sample_session.case_context.refund_reason = "CHANGED_MIND"
        sample_session.case_context.refund_store_credit_offered = True
        sample_session.case_context.customer_resolution_choice = "REFUND"
        
        decision = refund_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["changed_mind_cash_refund"]
        assert decision["tool_plan"][0]["tool_name"] == "shopify_refund_order"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
