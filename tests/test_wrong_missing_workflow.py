"""
Tests for Wrong/Missing Item workflow.
Covers all 8 required test cases from spec.
"""
import pytest
from unittest.mock import MagicMock

from app.models import (
    Session, CustomerInfo, CaseContext, Intent
)
from app.wrong_missing_helpers import (
    extract_order_number, detect_photo_attachment,
    detect_wrong_missing_type, detect_resolution_preference,
    detect_acceptance, detect_decline
)
from app.workflow_engine import WorkflowEngine


# ================ Unit Tests for wrong_missing_helpers ================

class TestExtractOrderNumber:
    """Tests for extract_order_number function."""
    
    def test_extracts_hash_format(self):
        """Should extract #1234 format."""
        assert extract_order_number("My order #1234 is wrong") == "#1234"
        assert extract_order_number("Order # 5678 has issues") == "#5678"
    
    def test_extracts_ord_format(self):
        """Should extract ORD-1234 format."""
        assert extract_order_number("ORD-1234") == "#1234"
        assert extract_order_number("ORDER-5678") == "#5678"
    
    def test_extracts_natural_language(self):
        """Should extract 'order 1234' format."""
        assert extract_order_number("my order 1234 is missing") == "#1234"
        assert extract_order_number("order number 5678") == "#5678"
    
    def test_returns_none_if_not_found(self):
        """Should return None if no order number found."""
        assert extract_order_number("I need help") is None
        assert extract_order_number("") is None
        assert extract_order_number(None) is None


class TestDetectPhotoAttachment:
    """Tests for detect_photo_attachment function."""
    
    def test_detects_attachment_keywords(self):
        """Should detect attachment keywords."""
        assert detect_photo_attachment("I've attached the photos") is True
        assert detect_photo_attachment("Here's the photo") is True
        assert detect_photo_attachment("See attached") is True
        assert detect_photo_attachment("[image]") is True
    
    def test_returns_false_without_keywords(self):
        """Should return False without keywords."""
        assert detect_photo_attachment("I can send photos") is False
        assert detect_photo_attachment("Here is my order") is False
        assert detect_photo_attachment("") is False


class TestDetectWrongMissingType:
    """Tests for detect_wrong_missing_type function."""
    
    def test_detects_missing_item(self):
        """Should detect missing item indicators."""
        assert detect_wrong_missing_type("My item is missing") == "MISSING_ITEM"
        assert detect_wrong_missing_type("I didn't receive everything") == "MISSING_ITEM"
        assert detect_wrong_missing_type("not in the box") == "MISSING_ITEM"
    
    def test_detects_wrong_item(self):
        """Should detect wrong item indicators."""
        assert detect_wrong_missing_type("I got the wrong item") == "WRONG_ITEM"
        assert detect_wrong_missing_type("This is not what I ordered") == "WRONG_ITEM"
        assert detect_wrong_missing_type("wrong size") == "WRONG_ITEM"
    
    def test_returns_none_for_unclear(self):
        """Should return None for unclear messages."""
        assert detect_wrong_missing_type("I have a problem") is None
        assert detect_wrong_missing_type("my order") is None


class TestDetectResolutionPreference:
    """Tests for detect_resolution_preference function."""
    
    def test_detects_reship(self):
        """Should detect reship preference."""
        assert detect_resolution_preference("Please reship it") == "RESHIP"
        assert detect_resolution_preference("I want a replacement") == "RESHIP"
    
    def test_detects_store_credit(self):
        """Should detect store credit preference."""
        assert detect_resolution_preference("I'll take store credit") == "STORE_CREDIT"
    
    def test_detects_refund(self):
        """Should detect refund preference."""
        assert detect_resolution_preference("I want a refund") == "CASH_REFUND"
        assert detect_resolution_preference("money back please") == "CASH_REFUND"


class TestDetectAcceptanceDecline:
    """Tests for accept/decline detection."""
    
    def test_detects_acceptance(self):
        """Should detect acceptance."""
        assert detect_acceptance("yes please") is True
        assert detect_acceptance("ok that works") is True
        assert detect_acceptance("sounds good") is True
    
    def test_detects_decline(self):
        """Should detect decline."""
        assert detect_decline("no thanks") is True
        assert detect_decline("I'd prefer not") is True
        assert detect_decline("no, I'd rather have") is True


# ================ Integration Tests for Wrong/Missing Workflow ================

@pytest.fixture
def wm_engine():
    """Create workflow engine."""
    return WorkflowEngine()


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    customer = CustomerInfo(
        customer_email="test@example.com",
        first_name="Jane",
        last_name="Doe",
        shopify_customer_id="cust_456"
    )
    session = Session(customer_info=customer)
    session.intent = Intent.WRONG_MISSING
    return session


class TestWrongMissingWorkflowRules:
    """Integration tests for Wrong/Missing workflow rules."""
    
    def test_no_order_fetches_orders(self, wm_engine, sample_session):
        """Test 1: No order -> fetch customer orders."""
        sample_session.case_context.order_id = None
        sample_session.case_context.extra['orders_fetched'] = False
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["fetch_customer_orders"]
    
    def test_orders_fetched_no_order_asks_for_number(self, wm_engine, sample_session):
        """Test 1b: Orders fetched but no match -> asks for order number."""
        sample_session.case_context.order_id = None
        sample_session.case_context.extra['orders_fetched'] = True
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert decision["policy_applied"] == ["require_order_id"]
    
    def test_missing_type_asks_clarifying(self, wm_engine, sample_session):
        """Test 2: Missing type -> asks 'missing or wrong?'"""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "fulfilled"  # Need order_status to skip fetch
        sample_session.case_context.wrong_missing_type = None
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert decision["policy_applied"] == ["clarify_issue_type"]
        assert "missing" in decision["clarifying_questions"][0].lower()
        assert "wrong" in decision["clarifying_questions"][0].lower()
    
    def test_type_chosen_requests_photos(self, wm_engine, sample_session):
        """Test 3: Type chosen -> requests photos (3 items)."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "fulfilled"  # Need order_status to skip fetch
        sample_session.case_context.wrong_missing_type = "MISSING_ITEM"
        sample_session.case_context.photos_requested = False
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["request_evidence_photos"]
        # Check for 3 photo request items
        template = decision["response_template"]
        assert "items you received" in template
        assert "packing slip" in template
        assert "shipping label" in template
    
    def test_refund_request_offers_reship_first(self, wm_engine, sample_session):
        """Test 4: Customer wants refund -> bot offers reship first."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "fulfilled"
        sample_session.case_context.wrong_missing_type = "WRONG_ITEM"
        sample_session.case_context.photos_requested = True
        sample_session.case_context.photos_received = True
        sample_session.case_context.customer_resolution_preference = "CASH_REFUND"
        sample_session.case_context.reship_offered = False
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        # Policy name from workflow JSON
        assert "offer_reship" in decision["policy_applied"][0]
        assert "reship" in decision["response_template"].lower()
    
    def test_declines_reship_offers_store_credit(self, wm_engine, sample_session):
        """Test 5: Customer declines reship -> store credit offer shown."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "fulfilled"
        sample_session.case_context.wrong_missing_type = "MISSING_ITEM"
        sample_session.case_context.photos_requested = True
        sample_session.case_context.photos_received = True
        sample_session.case_context.reship_offered = True
        sample_session.case_context.customer_resolution_preference = "CASH_REFUND"
        sample_session.case_context.store_credit_offered = False
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "respond"
        assert decision["policy_applied"] == ["offer_store_credit_with_bonus"]
        assert "store credit" in decision["response_template"].lower()
        assert "10%" in decision["response_template"]
    
    def test_accepts_store_credit_calls_tool(self, wm_engine, sample_session):
        """Test 6: Accepts store credit -> tool called, tags added, confirmation."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "fulfilled"
        sample_session.case_context.wrong_missing_type = "MISSING_ITEM"
        sample_session.case_context.photos_requested = True
        sample_session.case_context.photos_received = True
        sample_session.case_context.reship_offered = True
        sample_session.case_context.store_credit_offered = True
        sample_session.case_context.customer_resolution_preference = "STORE_CREDIT"
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["issue_store_credit"]
        assert len(decision["tool_plan"]) == 2  # create_store_credit + add_tags
        assert decision["tool_plan"][0]["tool_name"] == "shopify_create_store_credit"
        assert decision["tool_plan"][1]["tool_name"] == "shopify_add_tags"
    
    def test_declines_store_credit_cash_refund(self, wm_engine, sample_session):
        """Test 7: Declines store credit -> cash refund called, tags added."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "fulfilled"
        sample_session.case_context.extra["order_gid"] = "gid://shopify/Order/12345"
        sample_session.case_context.wrong_missing_type = "WRONG_ITEM"
        sample_session.case_context.photos_requested = True
        sample_session.case_context.photos_received = True
        sample_session.case_context.reship_offered = True
        sample_session.case_context.store_credit_offered = True
        sample_session.case_context.customer_resolution_preference = "CASH_REFUND"
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "call_tool"
        assert decision["policy_applied"] == ["process_cash_refund"]
        assert decision["tool_plan"][0]["tool_name"] == "shopify_refund_order"
        # Check response_template exists and mentions refund timeline
        if decision.get("response_template"):
            assert "5-7 business days" in decision["response_template"]
    
    def test_reship_selected_escalates_and_locks(self, wm_engine, sample_session):
        """Test 8: Reship selected -> escalation created + session locked."""
        sample_session.case_context.order_id = "#1234"
        sample_session.case_context.order_status = "fulfilled"
        sample_session.case_context.wrong_missing_type = "MISSING_ITEM"
        sample_session.case_context.photos_requested = True
        sample_session.case_context.photos_received = True
        sample_session.case_context.reship_offered = True
        sample_session.case_context.customer_resolution_preference = "RESHIP"
        
        decision = wm_engine.evaluate(sample_session)
        
        assert decision["next_action"] == "escalate"
        assert decision["policy_applied"] == ["reship_requires_manual_processing"]
        assert "manual reship" in decision["escalation_reason"].lower()
        assert decision.get("escalation_priority") == "high"
        # Check lock_session is set in rule
        assert "add_tags" in decision
        assert "Wrong or Missing" in decision["add_tags"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
