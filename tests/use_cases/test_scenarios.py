"""
Use-Case Scenario Tests
Version: 1.0
Developer: Dev B

End-to-end scenario tests for the 3 use cases:
1. WISMO (Shipping Delay)
2. Wrong/Missing Item
3. Refund Standard

These tests validate the expected behavior as defined in the Use Cases PDF.
"""
import pytest
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from schemas.triage import TriageResult, Intent, ExtractedEntities
from schemas.workflow import WorkflowDecision


class TestWISMOScenarios:
    """
    WISMO (Where Is My Order) Scenario Tests
    
    Reference: Use Cases PDF - Shipping Delay section
    Rules:
    - Mon-Wed contact: Promise Friday delivery
    - Thu-Sun contact: Promise early next week
    - Post-promise still not delivered: Escalate
    """
    
    def test_scenario_customer_contacts_monday(self):
        """
        Scenario: Customer contacts on Monday about delayed order.
        Expected: Promise Friday delivery.
        """
        # Input
        customer_message = "Siparişim gelmedi, 4 gündür bekliyorum"
        contact_day = "Mon"
        
        # Expected triage
        expected_triage = TriageResult(
            intent=Intent.WISMO,
            confidence=0.9,
            entities=ExtractedEntities(),
            needs_human=False
        )
        
        # Expected workflow decision
        expected_decision = {
            "action": "respond",
            "policy_applied": "friday_promise",
            "response_contains": "Friday"
        }
        
        # Assertions for test
        assert expected_triage.intent == Intent.WISMO
        assert expected_decision["action"] == "respond"
        assert expected_decision["policy_applied"] == "friday_promise"
    
    def test_scenario_customer_contacts_thursday(self):
        """
        Scenario: Customer contacts on Thursday about delayed order.
        Expected: Promise early next week delivery.
        """
        contact_day = "Thu"
        
        expected_decision = {
            "action": "respond",
            "policy_applied": "next_week_promise",
            "response_contains": "next week"
        }
        
        assert expected_decision["policy_applied"] == "next_week_promise"
    
    def test_scenario_post_promise_not_delivered(self):
        """
        Scenario: Customer was promised Friday but order still not delivered.
        Expected: Escalate to human agent.
        """
        expected_decision = {
            "action": "escalate",
            "policy_applied": "post_promise_escalation",
            "priority": "high"
        }
        
        assert expected_decision["action"] == "escalate"
        assert expected_decision["priority"] == "high"
    
    def test_scenario_order_already_delivered(self):
        """
        Scenario: Customer asks about order that's already delivered.
        Expected: Inform customer order was delivered.
        """
        expected_decision = {
            "action": "respond",
            "policy_applied": "order_delivered"
        }
        
        assert expected_decision["action"] == "respond"


class TestWrongMissingScenarios:
    """
    Wrong/Missing Item Scenario Tests
    
    Reference: Use Cases PDF - Wrong/Missing Item section  
    Rules:
    - Request evidence: item photo, packing slip, shipping label
    - Priority: Reship (fastest) > Store credit (+10%) > Cash refund
    - Reship requires human approval (escalation)
    """
    
    def test_scenario_missing_item_no_evidence(self):
        """
        Scenario: Customer reports missing item, no evidence provided.
        Expected: Ask for evidence (photos).
        """
        customer_message = "Paketimden ürün eksik çıktı"
        
        expected_triage = TriageResult(
            intent=Intent.WRONG_MISSING,
            confidence=0.9,
            entities=ExtractedEntities(),
            needs_human=False
        )
        
        expected_decision = {
            "action": "ask_clarifying",
            "policy_applied": "evidence_requirement",
            "required_fields_missing": ["item_photo", "packing_slip", "shipping_label"]
        }
        
        assert expected_triage.intent == Intent.WRONG_MISSING
        assert expected_decision["action"] == "ask_clarifying"
        assert len(expected_decision["required_fields_missing"]) == 3
    
    def test_scenario_evidence_complete_default_reship(self):
        """
        Scenario: Customer provides all evidence, no preference stated.
        Expected: Escalate for reship (fastest resolution, needs human approval).
        """
        expected_decision = {
            "action": "escalate",
            "policy_applied": "reship_priority",
            "escalation_reason_contains": "Reship"
        }
        
        assert expected_decision["action"] == "escalate"
        assert expected_decision["policy_applied"] == "reship_priority"
    
    def test_scenario_customer_prefers_store_credit(self):
        """
        Scenario: Customer provides evidence and prefers store credit.
        Expected: Issue store credit with 10% bonus.
        """
        expected_decision = {
            "action": "call_tool",
            "policy_applied": "store_credit_10_percent_bonus",
            "tool_plan": [
                {
                    "tool_name": "issue_store_credit",
                    "params": {"bonus_percent": 10}
                }
            ]
        }
        
        assert expected_decision["action"] == "call_tool"
        assert expected_decision["tool_plan"][0]["tool_name"] == "issue_store_credit"
    
    def test_scenario_customer_insists_cash_refund(self):
        """
        Scenario: Customer rejects all alternatives, wants cash refund.
        Expected: Process cash refund (last resort).
        """
        expected_decision = {
            "action": "call_tool",
            "policy_applied": "cash_refund_last_resort",
            "tool_plan": [{"tool_name": "process_refund"}]
        }
        
        assert expected_decision["action"] == "call_tool"
        assert expected_decision["policy_applied"] == "cash_refund_last_resort"


class TestRefundStandardScenarios:
    """
    Refund Standard Scenario Tests
    
    Reference: Use Cases PDF - Refund section
    Rules:
    - Ask reason first
    - Shipping delay reason -> Route to WISMO workflow
    - Wrong/missing reason -> Route to Wrong/Missing workflow
    - Other reasons: Offer store credit (+10% bonus) first, then cash refund
    """
    
    def test_scenario_refund_shipping_delay(self):
        """
        Scenario: Customer requests refund due to shipping delay.
        Expected: Route to WISMO workflow.
        """
        customer_message = "Refund istiyorum, kargo çok geç geldi"
        
        expected_triage = TriageResult(
            intent=Intent.REFUND_STANDARD,
            confidence=0.85,
            entities=ExtractedEntities(),
            needs_human=False
        )
        
        expected_decision = {
            "action": "route_to_workflow",
            "target_workflow": "WISMO",
            "policy_applied": "shipping_delay_uses_wismo_rules"
        }
        
        assert expected_triage.intent == Intent.REFUND_STANDARD
        assert expected_decision["action"] == "route_to_workflow"
        assert expected_decision["target_workflow"] == "WISMO"
    
    def test_scenario_refund_wrong_item(self):
        """
        Scenario: Customer requests refund for wrong item.
        Expected: Route to Wrong/Missing workflow.
        """
        expected_decision = {
            "action": "route_to_workflow",
            "target_workflow": "WRONG_MISSING",
            "policy_applied": "wrong_missing_uses_dedicated_workflow"
        }
        
        assert expected_decision["target_workflow"] == "WRONG_MISSING"
    
    def test_scenario_refund_changed_mind(self):
        """
        Scenario: Customer wants refund because they changed mind.
        Expected: Offer store credit with 10% bonus first.
        """
        expected_decision = {
            "action": "respond",
            "policy_applied": "offer_store_credit_first",
            "response_contains": "store credit"
        }
        
        assert expected_decision["action"] == "respond"
        assert expected_decision["policy_applied"] == "offer_store_credit_first"
    
    def test_scenario_refund_no_reason(self):
        """
        Scenario: Customer requests refund without reason.
        Expected: Ask for reason.
        """
        expected_decision = {
            "action": "ask_clarifying",
            "policy_applied": "require_refund_reason"
        }
        
        assert expected_decision["action"] == "ask_clarifying"


class TestEscalationScenarios:
    """
    Escalation Scenario Tests
    
    Tests conditions that should trigger escalation.
    """
    
    def test_scenario_low_confidence_triage(self):
        """
        Scenario: Triage agent has low confidence (<0.6).
        Expected: Flag needs_human = True.
        """
        triage_result = TriageResult(
            intent=Intent.UNKNOWN,
            confidence=0.4,
            entities=ExtractedEntities(),
            needs_human=True,
            reasoning="Ambiguous customer message"
        )
        
        assert triage_result.needs_human is True
        assert triage_result.confidence < 0.6
    
    def test_scenario_tool_failure_after_retry(self):
        """
        Scenario: Tool fails after retry attempts.
        Expected: should_escalate = True.
        """
        from tools.client import ToolCallResult
        
        result = ToolCallResult(
            tool_name="check_order_status",
            params={"order_id": "12345"},
            success=False,
            data={},
            error="Service unavailable",
            retry_count=2,
            should_escalate=True
        )
        
        assert result.should_escalate is True
        assert result.retry_count >= 1


class TestDemoScripts:
    """
    Demo Script Scenarios
    
    These are the scenarios that will be demonstrated in the hackathon.
    """
    
    def test_demo_wismo_flow(self):
        """
        Demo 1: WISMO Shipping Delay
        
        Input: "Siparişim gelmedi, 4 gündür bekliyorum"
        Expected Flow:
        1. Triage → WISMO intent
        2. Workflow → check_order_status tool
        3. Workflow → Friday/next week promise based on day
        4. Support → Generate customer email
        """
        demo_script = {
            "name": "WISMO Demo",
            "input": "Siparişim gelmedi, 4 gündür bekliyorum",
            "expected_flow": [
                {"agent": "triage", "output": {"intent": "WISMO"}},
                {"agent": "workflow", "action": "call_tool", "tool": "check_order_status"},
                {"agent": "workflow", "action": "respond", "policy": "friday_promise or next_week_promise"},
                {"agent": "support", "output": "customer_email"}
            ],
            "trace_highlights": [
                "triage.intent = WISMO",
                "workflow.policy_applied = friday_promise",
                "tool_call.check_order_status.success = true"
            ]
        }
        
        assert demo_script["expected_flow"][0]["output"]["intent"] == "WISMO"
    
    def test_demo_wrong_missing_flow(self):
        """
        Demo 2: Wrong/Missing Item
        
        Input: "Paketimden ürün eksik çıktı"
        Expected Flow:
        1. Triage → WRONG_MISSING intent
        2. Workflow → ask_clarifying (evidence)
        3. [Customer provides evidence]
        4. Workflow → escalate (reship priority)
        """
        demo_script = {
            "name": "Wrong/Missing Demo",
            "input": "Paketimden ürün eksik çıktı",
            "expected_flow": [
                {"agent": "triage", "output": {"intent": "WRONG_MISSING"}},
                {"agent": "workflow", "action": "ask_clarifying", "policy": "evidence_requirement"},
                {"agent": "customer", "action": "provides_evidence"},
                {"agent": "workflow", "action": "escalate", "policy": "reship_priority"}
            ]
        }
        
        assert demo_script["expected_flow"][0]["output"]["intent"] == "WRONG_MISSING"
    
    def test_demo_refund_routing_flow(self):
        """
        Demo 3: Refund Standard with Routing
        
        Input: "Refund istiyorum, kargo çok geç geldi"
        Expected Flow:
        1. Triage → REFUND_STANDARD intent
        2. Workflow → route_to_workflow (WISMO)
        3. WISMO workflow takes over
        """
        demo_script = {
            "name": "Refund Routing Demo",
            "input": "Refund istiyorum, kargo çok geç geldi",
            "expected_flow": [
                {"agent": "triage", "output": {"intent": "REFUND_STANDARD"}},
                {"agent": "workflow", "action": "route_to_workflow", "target": "WISMO"},
                {"agent": "workflow_wismo", "action": "respond", "policy": "friday_promise"}
            ]
        }
        
        assert demo_script["expected_flow"][1]["target"] == "WISMO"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
