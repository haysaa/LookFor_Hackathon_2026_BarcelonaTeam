"""
WorkflowEngine - Deterministic decision tree evaluator.
Loads JSON workflow definitions and evaluates conditions to produce decisions.
"""
import json
import os
from typing import Optional, Any
from pathlib import Path


class WorkflowEngine:
    """
    Evaluates deterministic workflow rules based on session context.
    
    Loads JSON workflow files and evaluates conditions to produce
    WorkflowDecision objects for the orchestrator.
    """
    
    def __init__(self, workflows_dir: Optional[str] = None):
        """
        Initialize WorkflowEngine.
        
        Args:
            workflows_dir: Path to workflows directory (defaults to project's workflows/)
        """
        if workflows_dir:
            self.workflows_dir = Path(workflows_dir)
        else:
            # Default to project's workflows directory
            project_root = Path(__file__).parent.parent
            self.workflows_dir = project_root / "workflows"
        
        self.workflows = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """Load all workflow JSON files."""
        if not self.workflows_dir.exists():
            return
        
        for file in self.workflows_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                    name = workflow.get("workflow_name", file.stem.upper())
                    self.workflows[name] = workflow
            except Exception as e:
                print(f"Warning: Failed to load workflow {file}: {e}")
    
    def evaluate(self, session) -> dict:
        """
        Evaluate workflow rules based on session state.
        
        Args:
            session: Session object with intent and case_context
        
        Returns:
            dict with workflow decision
        """
        intent = str(session.intent.value) if hasattr(session.intent, 'value') else str(session.intent)
        workflow = self.workflows.get(intent)
        
        if not workflow:
            # Fallback for unknown intent
            return {
                "workflow_id": intent,
                "next_action": "respond",
                "policy_applied": ["default_response"],
                "required_fields_missing": [],
                "tool_plan": [],
                "response_template": "Thank you for contacting us. How can I assist you today?"
            }
        
        # Build context from session
        context = self._build_context(session)
        
        # Evaluate rules in order
        for rule in workflow.get("rules", []):
            if self._evaluate_condition(rule.get("condition", {}), context):
                return self._build_decision(workflow, rule, context)
        
        # No rules matched - default respond
        return {
            "workflow_id": intent,
            "next_action": "respond",
            "policy_applied": ["no_matching_rule"],
            "required_fields_missing": [],
            "tool_plan": [],
            "response_template": "I'm looking into your request. Is there anything specific I can help with?"
        }
    
    def _build_context(self, session) -> dict:
        """Build context dict from session for condition evaluation."""
        ctx = {}
        
        # Case context fields
        if hasattr(session, 'case_context'):
            cc = session.case_context
            ctx['order_id'] = getattr(cc, 'order_id', None)
            ctx['order_status'] = getattr(cc, 'order_status', None)
            ctx['tracking_number'] = getattr(cc, 'tracking_number', None)
            ctx['tracking_url'] = getattr(cc, 'tracking_url', None)
            ctx['item_name'] = getattr(cc, 'item_name', None)
            ctx['order_date'] = getattr(cc, 'order_date', None)
            ctx['shipping_status'] = getattr(cc, 'shipping_status', None)
            ctx['refund_reason'] = getattr(cc, 'refund_reason', None)
            ctx['promise_given'] = getattr(cc, 'promise_given', None)
            ctx['item_photo'] = getattr(cc, 'item_photo', None)
            ctx['packing_slip'] = getattr(cc, 'packing_slip', None)
            ctx['orders_fetched'] = getattr(cc, 'extra', {}).get('orders_fetched', None)
            ctx['tracking_requested'] = getattr(cc, 'extra', {}).get('tracking_requested', None)
            
            # WISMO fields
            ctx['wismo_promise_type'] = getattr(cc, 'wismo_promise_type', None)
            ctx['wismo_promise_deadline'] = getattr(cc, 'wismo_promise_deadline', None)
            ctx['wismo_promise_set_at'] = getattr(cc, 'wismo_promise_set_at', None)
            
            # Wrong/Missing fields
            ctx['wrong_missing_type'] = getattr(cc, 'wrong_missing_type', None)
            ctx['photos_requested'] = getattr(cc, 'photos_requested', False)
            ctx['photos_received'] = getattr(cc, 'photos_received', False)
            ctx['reship_offered'] = getattr(cc, 'reship_offered', False)
            ctx['store_credit_offered'] = getattr(cc, 'store_credit_offered', False)
            ctx['customer_resolution_preference'] = getattr(cc, 'customer_resolution_preference', None)
            
            # Refund workflow fields
            ctx['refund_reason'] = getattr(cc, 'refund_reason', None)
            ctx['expectation_cause'] = getattr(cc, 'expectation_cause', None)
            ctx['usage_tip_sent'] = getattr(cc, 'usage_tip_sent', False)
            ctx['swap_offered'] = getattr(cc, 'swap_offered', False)
            ctx['refund_store_credit_offered'] = getattr(cc, 'refund_store_credit_offered', False)
            ctx['refund_shipping_promise_type'] = getattr(cc, 'refund_shipping_promise_type', None)
            ctx['refund_shipping_promise_deadline'] = getattr(cc, 'refund_shipping_promise_deadline', None)
            ctx['refund_shipping_wait_asked'] = getattr(cc, 'refund_shipping_wait_asked', False)
            ctx['customer_wait_acceptance'] = getattr(cc, 'customer_wait_acceptance', None)
            ctx['replacement_offered'] = getattr(cc, 'replacement_offered', False)
            ctx['customer_resolution_choice'] = getattr(cc, 'customer_resolution_choice', None)
            
            # Auto-compute contact_day if not set
            contact_day = getattr(cc, 'contact_day', None)
            if not contact_day:
                try:
                    from app.wismo_helpers import get_contact_day
                    contact_day = get_contact_day(session)
                except ImportError:
                    pass
            ctx['contact_day'] = contact_day
            
            # Compute deadline_passed dynamically
            deadline = getattr(cc, 'wismo_promise_deadline', None)
            if deadline:
                try:
                    from app.wismo_helpers import is_promise_deadline_passed
                    ctx['wismo_promise_deadline_passed'] = is_promise_deadline_passed(deadline)
                except ImportError:
                    ctx['wismo_promise_deadline_passed'] = False
            else:
                ctx['wismo_promise_deadline_passed'] = False
        
        # Customer info
        if hasattr(session, 'customer_info'):
            ci = session.customer_info
            ctx['customer_id'] = getattr(ci, 'shopify_customer_id', None)
            ctx['customer_email'] = getattr(ci, 'customer_email', None)
        
        return ctx
    
    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        """Evaluate a single condition or compound condition."""
        if not condition:
            return True
        
        # Compound conditions
        if "all" in condition:
            return all(self._evaluate_condition(c, context) for c in condition["all"])
        
        if "any" in condition:
            return any(self._evaluate_condition(c, context) for c in condition["any"])
        
        # Simple condition
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if not field or not operator:
            return True
        
        actual = context.get(field)
        
        # Operators
        if operator == "is_null":
            return actual is None or actual == ""
        
        if operator == "is_not_null" or operator == "not_null":
            return actual is not None and actual != ""
        
        if operator == "equals":
            return actual == value
        
        if operator == "not_equals":
            return actual != value
        
        if operator == "in":
            return actual in value if value else False
        
        if operator == "not_in":
            return actual not in value if value else True
        
        if operator == "contains":
            return value in str(actual) if actual else False
        
        return False
    
    def _build_decision(self, workflow: dict, rule: dict, context: dict) -> dict:
        """Build a decision dict from a matched rule."""
        action = rule.get("action", "respond")
        
        decision = {
            "workflow_id": workflow.get("workflow_name", "UNKNOWN"),
            "rule_id": rule.get("id", "unknown"),
            "next_action": action,
            "policy_applied": [rule.get("policy_applied", rule.get("id", "unknown"))],
            "required_fields_missing": [],
            "tool_plan": [],
            "response_template": None,
            "clarifying_questions": [],
            "escalation_reason": None,
            "escalation_priority": rule.get("priority", "medium"),
            "set_context": rule.get("set_context", {}),
            "add_tags": rule.get("add_tags", [])
        }
        
        # Handle specific actions
        if action == "ask_clarifying":
            response = rule.get("response", {})
            decision["clarifying_questions"] = response.get("clarifying_questions", [])
            # Find what fields are actually missing
            for field in workflow.get("required_fields", []):
                if not context.get(field):
                    decision["required_fields_missing"].append(field)
        
        elif action == "call_tool":
            tool_plan = rule.get("tool_plan", [])
            for tp in tool_plan:
                resolved_params = {}
                params_source = tp.get("params_source", {})
                for param_name, source in params_source.items():
                    if isinstance(source, str) and source.startswith("context."):
                        ctx_field = source.replace("context.", "")
                        resolved_params[param_name] = context.get(ctx_field)
                    else:
                        resolved_params[param_name] = source
                
                decision["tool_plan"].append({
                    "tool_name": tp.get("tool_name"),
                    "params": resolved_params
                })
        
        elif action == "respond":
            decision["response_template"] = rule.get("response_template")
            # Interpolate context values in template
            if decision["response_template"]:
                for key, value in context.items():
                    if value is not None:
                        decision["response_template"] = decision["response_template"].replace(
                            f"{{{key}}}", str(value)
                        )
        
        elif action == "escalate":
            decision["escalation_reason"] = rule.get("escalation_reason", "Rule triggered escalation")
            # Include response_template for escalation messages (e.g., Monica loop-in)
            if rule.get("response_template"):
                decision["response_template"] = rule.get("response_template")
        
        return decision


# Global instance
workflow_engine = WorkflowEngine()
