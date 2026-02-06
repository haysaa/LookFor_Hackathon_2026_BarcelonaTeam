"""
Unit tests for WorkflowEngine.
Tests deterministic policy decisions from JSON workflows.
"""
import pytest
from app.models import Session, CustomerInfo, Intent, CaseContext
from app.workflow import WorkflowEngine


class TestWorkflowEngine:
    """Unit tests for WorkflowEngine."""
    
    def setup_method(self):
        """Create workflow engine with test workflows."""
        self.engine = WorkflowEngine(workflows_dir="workflows")
    
    def _create_session(
        self,
        intent: Intent = Intent.WISMO,
        order_id: str = "ORD-123",
        contact_day: str = "Mon",
        **context_kwargs
    ) -> Session:
        """Helper to create a test session."""
        customer = CustomerInfo(
            customer_email="test@example.com",
            first_name="Test",
            last_name="User",
            shopify_customer_id="cust_123"
        )
        case_context = CaseContext(
            order_id=order_id,
            contact_day=contact_day,
            **context_kwargs
        )
        session = Session(customer_info=customer)
        session.intent = intent
        session.case_context = case_context
        return session
    
    # --- WISMO Tests ---
    
    def test_wismo_monday_friday_promise(self):
        """WISMO on Mon-Wed should give Friday promise."""
        for day in ["Mon", "Tue", "Wed"]:
            session = self._create_session(
                intent=Intent.WISMO,
                contact_day=day
            )
            decision = self.engine.evaluate(session)
            
            assert decision["next_action"] == "respond"
            assert "friday_promise" in decision["policy_applied"]
            assert "Cuma" in decision.get("response_template", "")
    
    def test_wismo_thursday_next_week_promise(self):
        """WISMO on Thu-Sun should give next week promise."""
        for day in ["Thu", "Fri", "Sat", "Sun"]:
            session = self._create_session(
                intent=Intent.WISMO,
                contact_day=day
            )
            decision = self.engine.evaluate(session)
            
            assert decision["next_action"] == "respond"
            assert "next_week_promise" in decision["policy_applied"]
            assert "hafta" in decision.get("response_template", "").lower()
    
    def test_wismo_missing_order_id(self):
        """WISMO without order_id should ask for clarification."""
        session = self._create_session(
            intent=Intent.WISMO,
            order_id=None  # Missing!
        )
        decision = self.engine.evaluate(session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert "order_id" in decision["required_fields_missing"]
    
    # --- Wrong/Missing Tests ---
    
    def test_wrong_missing_evidence_missing(self):
        """Wrong/Missing without evidence should ask for photos."""
        session = self._create_session(
            intent=Intent.WRONG_MISSING,
            item_name="Blue T-Shirt"
        )
        # Evidence defaults to False
        decision = self.engine.evaluate(session)
        
        assert decision["next_action"] == "ask_clarifying"
        assert "evidence_requirement" in decision["policy_applied"]
    
    def test_wrong_missing_evidence_complete_escalates(self):
        """Wrong/Missing with full evidence should escalate for reship."""
        session = self._create_session(
            intent=Intent.WRONG_MISSING,
            item_name="Blue T-Shirt"
        )
        # Set all evidence to True
        session.case_context.evidence = {
            "item_photo": True,
            "packing_slip": True,
            "shipping_label": True
        }
        decision = self.engine.evaluate(session)
        
        assert decision["next_action"] == "escalate"
        assert "reship_priority" in decision["policy_applied"]
    
    # --- Refund Standard Tests ---
    
    def test_refund_shipping_delay_routes_to_wismo(self):
        """Refund with shipping_delay reason should route to WISMO."""
        session = self._create_session(
            intent=Intent.REFUND_STANDARD,
            refund_reason="shipping_delay"
        )
        decision = self.engine.evaluate(session)
        
        assert decision["next_action"] == "route_to_workflow"
        assert decision["target_workflow"] == "WISMO"
    
    def test_refund_wrong_missing_routes(self):
        """Refund with wrong_missing reason should route to Wrong/Missing workflow."""
        session = self._create_session(
            intent=Intent.REFUND_STANDARD,
            refund_reason="wrong_missing"
        )
        decision = self.engine.evaluate(session)
        
        assert decision["next_action"] == "route_to_workflow"
        assert decision["target_workflow"] == "WRONG_MISSING"
    
    def test_refund_no_reason_asks_clarifying(self):
        """Refund without reason should ask for clarification."""
        session = self._create_session(
            intent=Intent.REFUND_STANDARD,
            refund_reason=None
        )
        decision = self.engine.evaluate(session)
        
        # Should either ask for refund_reason or have it as required field
        assert decision["next_action"] in ["ask_clarifying"]
        assert "refund_reason" in decision.get("required_fields_missing", [])
    
    # --- Edge Cases ---
    
    def test_unknown_intent_escalates(self):
        """Unknown intent should escalate."""
        session = self._create_session(intent=Intent.UNKNOWN)
        decision = self.engine.evaluate(session)
        
        assert decision["next_action"] == "escalate"
        assert "no_matching_workflow" in decision["policy_applied"]
