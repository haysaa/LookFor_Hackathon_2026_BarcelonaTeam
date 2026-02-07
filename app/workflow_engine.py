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
                # Check for policy override BEFORE building decision
                workflow_name = workflow.get("workflow_name", intent)
                rule_id = rule.get("id", "unknown")
                
                decision = self._build_decision(workflow, rule, context, workflow_name, rule_id)
                return decision
        
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
            ctx['tracking_number'] = getattr(cc, 'tracking_number', None)
            ctx['item_name'] = getattr(cc, 'item_name', None)
            ctx['order_date'] = getattr(cc, 'order_date', None)
            ctx['shipping_status'] = getattr(cc, 'shipping_status', None)
            ctx['contact_day'] = getattr(cc, 'contact_day', None)
            ctx['refund_reason'] = getattr(cc, 'refund_reason', None)
            ctx['promise_given'] = getattr(cc, 'promise_given', None)
            ctx['item_photo'] = getattr(cc, 'item_photo', None)
            ctx['packing_slip'] = getattr(cc, 'packing_slip', None)
        
        # Customer info
        if hasattr(session, 'customer_info'):
            ci = session.customer_info
            ctx['customer_id'] = getattr(ci, 'shopify_customer_id', None)
            ctx['customer_email'] = getattr(ci, 'email', None)
        
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
        
        if operator == "is_not_null":
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
    
    
    def _build_decision(self, workflow: dict, rule: dict, context: dict, workflow_name: str, rule_id: str) -> dict:
        """Build a decision dict from a matched rule, applying policy overrides if exists."""
        action = rule.get("action", "respond")
        
        # CHECK FOR POLICY OVERRIDE
        from app.policy_overrides import get_policy_store
        
        policy_store = get_policy_store()
        override = policy_store.get_override(workflow_name, rule_id)
        
        # Build base decision
        decision = {
            "workflow_id": workflow_name,
            "next_action": action,
            "policy_applied": [rule.get("policy_applied", rule.get("id", "unknown"))],
            "required_fields_missing": [],
            "tool_plan": [],
            "response_template": None,
            "clarifying_questions": [],
            "escalation_reason": None,
            "policy_override_applied": False
        }
        
        # APPLY OVERRIDE IF EXISTS
        if override and override.active:
            # Override the action
            action = override.override_action
            decision["next_action"] = action
            decision["policy_override_applied"] = True
            decision["override_id"] = override.override_id
            
            # Apply context updates (e.g., NEEDS_ATTENTION: true)
            if override.context_updates:
                for key, value in override.context_updates.items():
                    context[key] = value
                decision["context_updates_applied"] = override.context_updates
            
            # Override escalation reason if provided
            if override.escalation_reason:
                decision["escalation_reason"] = override.escalation_reason
            
            # Override response template if provided
            if override.response_template_override:
                decision["response_template"] = override.response_template_override
            
            # Log override in trace (will be picked up by orchestrator)
            decision["trace_note"] = f"Policy override '{override.override_id}' applied: {override.original_prompt[:100]}"
        
        # Handle specific actions (with potential override modifications)
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
                    if source.startswith("context."):
                        ctx_field = source.replace("context.", "")
                        resolved_params[param_name] = context.get(ctx_field)
                    else:
                        resolved_params[param_name] = source
                
                # Apply tool param overrides if exists
                if override and override.tool_param_overrides:
                    resolved_params.update(override.tool_param_overrides)
                
                decision["tool_plan"].append({
                    "tool_name": tp.get("tool_name"),
                    "params": resolved_params
                })
        
        elif action == "respond":
            if not decision["response_template"]:  # Only if not overridden
                decision["response_template"] = rule.get("response_template")
        
        elif action == "escalate":
            if not decision["escalation_reason"]:  # Only if not overridden
                decision["escalation_reason"] = rule.get("escalation_reason", "Rule triggered escalation")
        
        return decision


# Global instance
workflow_engine = WorkflowEngine()
