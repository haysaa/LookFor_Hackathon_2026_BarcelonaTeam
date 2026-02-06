"""
Unit Tests - Workflow Decision Trees
Version: 1.0
Developer: Dev B

Tests workflow JSON structure and decision logic.
"""
import pytest
import json
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestWorkflowJSONStructure:
    """Test workflow JSON files have correct structure."""
    
    WORKFLOWS_DIR = Path(__file__).parent.parent.parent / "workflows"
    
    @pytest.fixture
    def wismo_workflow(self):
        """Load WISMO workflow."""
        with open(self.WORKFLOWS_DIR / "wismo.json") as f:
            return json.load(f)
    
    @pytest.fixture
    def wrong_missing_workflow(self):
        """Load Wrong/Missing workflow."""
        with open(self.WORKFLOWS_DIR / "wrong_missing.json") as f:
            return json.load(f)
    
    @pytest.fixture
    def refund_workflow(self):
        """Load Refund Standard workflow."""
        with open(self.WORKFLOWS_DIR / "refund_standard.json") as f:
            return json.load(f)
    
    def test_wismo_structure(self, wismo_workflow):
        """Test WISMO workflow has required fields."""
        assert wismo_workflow["workflow_name"] == "WISMO"
        assert "version" in wismo_workflow
        assert "rules" in wismo_workflow
        assert "required_fields" in wismo_workflow
        assert len(wismo_workflow["rules"]) >= 5
    
    def test_wrong_missing_structure(self, wrong_missing_workflow):
        """Test Wrong/Missing workflow has required fields."""
        assert wrong_missing_workflow["workflow_name"] == "WRONG_MISSING"
        assert "evidence_fields" in wrong_missing_workflow
        assert "priority_order" in wrong_missing_workflow
        assert wrong_missing_workflow["priority_order"] == ["reship", "store_credit", "cash_refund"]
    
    def test_refund_structure(self, refund_workflow):
        """Test Refund Standard workflow has required fields."""
        assert refund_workflow["workflow_name"] == "REFUND_STANDARD"
        assert "rules" in refund_workflow
        # Check routing rules exist
        rule_actions = [r["action"] for r in refund_workflow["rules"]]
        assert "route_to_workflow" in rule_actions


class TestWISMOWorkflowRules:
    """Test WISMO workflow decision logic."""
    
    @pytest.fixture
    def workflow(self):
        """Load WISMO workflow."""
        path = Path(__file__).parent.parent.parent / "workflows" / "wismo.json"
        with open(path) as f:
            return json.load(f)
    
    def test_friday_promise_rule_exists(self, workflow):
        """Test Mon-Wed Friday promise rule exists."""
        friday_rules = [r for r in workflow["rules"] 
                       if r.get("policy_applied") == "friday_promise"]
        assert len(friday_rules) == 1
        assert friday_rules[0]["action"] == "respond"
    
    def test_next_week_promise_rule_exists(self, workflow):
        """Test Thu-Sun next week promise rule exists."""
        next_week_rules = [r for r in workflow["rules"] 
                          if r.get("policy_applied") == "next_week_promise"]
        assert len(next_week_rules) == 1
        assert next_week_rules[0]["action"] == "respond"
    
    def test_post_promise_escalation_exists(self, workflow):
        """Test post-promise escalation rule exists."""
        escalation_rules = [r for r in workflow["rules"] 
                           if r.get("policy_applied") == "post_promise_escalation"]
        assert len(escalation_rules) == 1
        assert escalation_rules[0]["action"] == "escalate"
        assert escalation_rules[0].get("priority") == "high"


class TestWrongMissingWorkflowRules:
    """Test Wrong/Missing workflow decision logic."""
    
    @pytest.fixture
    def workflow(self):
        """Load Wrong/Missing workflow."""
        path = Path(__file__).parent.parent.parent / "workflows" / "wrong_missing.json"
        with open(path) as f:
            return json.load(f)
    
    def test_evidence_requirement_rule(self, workflow):
        """Test evidence requirement rule exists."""
        evidence_rules = [r for r in workflow["rules"] 
                         if r.get("policy_applied") == "evidence_requirement"]
        assert len(evidence_rules) == 1
        assert evidence_rules[0]["action"] == "ask_clarifying"
    
    def test_reship_priority_rule(self, workflow):
        """Test reship priority rule exists."""
        reship_rules = [r for r in workflow["rules"] 
                       if r.get("policy_applied") == "reship_priority"]
        assert len(reship_rules) == 1
        # Reship requires human approval (escalation)
        assert reship_rules[0]["action"] == "escalate"
    
    def test_store_credit_bonus_rule(self, workflow):
        """Test 10% store credit bonus rule exists."""
        credit_rules = [r for r in workflow["rules"] 
                       if r.get("policy_applied") == "store_credit_10_percent_bonus"]
        assert len(credit_rules) == 1
        assert credit_rules[0]["action"] == "call_tool"
        assert credit_rules[0]["tool_plan"][0]["tool_name"] == "issue_store_credit"


class TestRefundWorkflowRules:
    """Test Refund Standard workflow decision logic."""
    
    @pytest.fixture
    def workflow(self):
        """Load Refund Standard workflow."""
        path = Path(__file__).parent.parent.parent / "workflows" / "refund_standard.json"
        with open(path) as f:
            return json.load(f)
    
    def test_shipping_delay_routing(self, workflow):
        """Test shipping delay routes to WISMO."""
        routing_rules = [r for r in workflow["rules"] 
                        if r.get("target_workflow") == "WISMO"]
        assert len(routing_rules) >= 1
        assert routing_rules[0]["action"] == "route_to_workflow"
    
    def test_wrong_missing_routing(self, workflow):
        """Test wrong/missing routes to WRONG_MISSING."""
        routing_rules = [r for r in workflow["rules"] 
                        if r.get("target_workflow") == "WRONG_MISSING"]
        assert len(routing_rules) >= 1
        assert routing_rules[0]["action"] == "route_to_workflow"
    
    def test_store_credit_offer_rule(self, workflow):
        """Test store credit is offered first."""
        offer_rules = [r for r in workflow["rules"] 
                      if r.get("policy_applied") == "offer_store_credit_first"]
        assert len(offer_rules) == 1
        assert offer_rules[0]["action"] == "respond"


class TestWorkflowFixtures:
    """Test with workflow fixtures from JSON file."""
    
    @pytest.fixture
    def fixtures(self):
        """Load workflow test fixtures."""
        path = Path(__file__).parent.parent / "fixtures" / "workflow_fixtures.json"
        with open(path) as f:
            return json.load(f)
    
    def test_fixtures_load(self, fixtures):
        """Test that fixtures load correctly."""
        assert "workflows" in fixtures
        assert "WISMO" in fixtures["workflows"]
        assert "WRONG_MISSING" in fixtures["workflows"]
        assert "REFUND_STANDARD" in fixtures["workflows"]
    
    def test_wismo_fixtures_count(self, fixtures):
        """Test WISMO has at least 3 fixtures."""
        wismo_fixtures = fixtures["workflows"]["WISMO"]["fixtures"]
        assert len(wismo_fixtures) >= 3
    
    def test_wrong_missing_fixtures_count(self, fixtures):
        """Test Wrong/Missing has at least 3 fixtures."""
        wm_fixtures = fixtures["workflows"]["WRONG_MISSING"]["fixtures"]
        assert len(wm_fixtures) >= 3
    
    def test_refund_fixtures_count(self, fixtures):
        """Test Refund Standard has at least 3 fixtures."""
        refund_fixtures = fixtures["workflows"]["REFUND_STANDARD"]["fixtures"]
        assert len(refund_fixtures) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
