"""
Workflow Engine - Deterministic policy decision engine.
Loads JSON decision trees and evaluates them against session state.
NO LLM calls here - all decisions are deterministic.
"""
import json
import os
from typing import Optional, Any
from pathlib import Path


class WorkflowDecision:
    """Result of workflow evaluation."""
    
    def __init__(
        self,
        workflow_id: str,
        next_action: str,  # ask_clarifying | call_tool | respond | escalate | route_to_workflow
        policy_applied: list[str],
        required_fields_missing: Optional[list[str]] = None,
        tool_plan: Optional[list[str]] = None,
        response_template: Optional[str] = None,
        escalation_reason: Optional[str] = None,
        target_workflow: Optional[str] = None
    ):
        self.workflow_id = workflow_id
        self.next_action = next_action
        self.policy_applied = policy_applied
        self.required_fields_missing = required_fields_missing or []
        self.tool_plan = tool_plan or []
        self.response_template = response_template
        self.escalation_reason = escalation_reason
        self.target_workflow = target_workflow
    
    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "next_action": self.next_action,
            "policy_applied": self.policy_applied,
            "required_fields_missing": self.required_fields_missing,
            "tool_plan": self.tool_plan,
            "response_template": self.response_template,
            "escalation_reason": self.escalation_reason,
            "target_workflow": self.target_workflow
        }


class WorkflowEngine:
    """
    Deterministic workflow engine that loads JSON decision trees.
    
    Key principle: NO LLM calls. All policy decisions are made via
    JSON rule matching. LLM is only used for text generation (Support Agent).
    """
    
    def __init__(self, workflows_dir: str = "workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.workflows: dict[str, dict] = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """Load all workflow JSON files from the workflows directory."""
        if not self.workflows_dir.exists():
            return
        
        for json_file in self.workflows_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    workflow = json.load(f)
                    name = workflow.get("workflow_name", json_file.stem.upper())
                    self.workflows[name] = workflow
            except Exception as e:
                print(f"Error loading workflow {json_file}: {e}")
    
    def reload_workflows(self):
        """Reload workflows from disk (for hot-reload during development)."""
        self.workflows.clear()
        self._load_workflows()
    
    def evaluate(self, session) -> dict:
        """
        Evaluate the appropriate workflow for the session.
        
        Args:
            session: Session object with intent, case_context, etc.
        
        Returns:
            WorkflowDecision as dict
        """
        # Determine which workflow to use based on intent
        intent = session.intent.value if session.intent else "UNKNOWN"
        workflow = self.workflows.get(intent)
        
        if not workflow:
            # No workflow found - escalate or use default
            return WorkflowDecision(
                workflow_id="default",
                next_action="escalate",
                policy_applied=["no_matching_workflow"],
                escalation_reason=f"No workflow found for intent: {intent}"
            ).to_dict()
        
        # Check required fields first
        missing_fields = self._check_required_fields(workflow, session)
        if missing_fields:
            return WorkflowDecision(
                workflow_id=workflow.get("workflow_name", "unknown"),
                next_action="ask_clarifying",
                policy_applied=["required_fields_check"],
                required_fields_missing=missing_fields
            ).to_dict()
        
        # Evaluate rules in order
        context = self._build_context(session)
        for rule in workflow.get("rules", []):
            if self._evaluate_condition(rule.get("condition", ""), context):
                return self._build_decision_from_rule(workflow, rule)
        
        # No rule matched - default to escalate
        return WorkflowDecision(
            workflow_id=workflow.get("workflow_name", "unknown"),
            next_action="escalate",
            policy_applied=["no_rule_matched"],
            escalation_reason="No matching rule in workflow"
        ).to_dict()
    
    def _check_required_fields(self, workflow: dict, session) -> list[str]:
        """Check if all required fields are present in session context."""
        required = workflow.get("required_fields", [])
        context = session.case_context
        missing = []
        
        for field in required:
            if field == "order_id" and not context.order_id:
                missing.append("order_id")
            elif field == "tracking_number" and not context.tracking_number:
                # tracking_number is optional for some workflows
                pass
            elif field == "item_name" and not context.item_name:
                missing.append("item_name")
            elif field == "refund_reason" and not context.refund_reason:
                missing.append("refund_reason")
            elif field in ["item_photo", "packing_slip", "shipping_label"]:
                if not context.evidence.get(field, False):
                    missing.append(field)
        
        return missing
    
    def _build_context(self, session) -> dict:
        """Build evaluation context from session."""
        ctx = session.case_context
        return {
            "order_id": ctx.order_id,
            "tracking_number": ctx.tracking_number,
            "item_name": ctx.item_name,
            "refund_reason": ctx.refund_reason,
            "contact_day": ctx.contact_day,
            "promise_given": ctx.promise_given,
            "promise_date": ctx.promise_date,
            "evidence_missing": not all(ctx.evidence.values()),
            "evidence_complete": all(ctx.evidence.values()),
            "intent": session.intent.value if session.intent else "UNKNOWN",
            "confidence": session.confidence,
            # Add more context as needed
            **ctx.extra
        }
    
    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """
        Evaluate a rule condition against context.
        
        Supports simple conditions like:
        - "contact_day in ['Mon', 'Tue', 'Wed']"
        - "evidence_missing"
        - "refund_reason == 'shipping_delay'"
        - "true" (always match)
        """
        if not condition or condition.lower() == "true":
            return True
        
        try:
            # Safe evaluation with limited context
            # SECURITY: Only allow specific operations
            safe_context = {
                **context,
                "True": True,
                "False": False,
                "None": None
            }
            result = eval(condition, {"__builtins__": {}}, safe_context)
            return bool(result)
        except Exception:
            # If condition fails to evaluate, don't match
            return False
    
    def _build_decision_from_rule(self, workflow: dict, rule: dict) -> dict:
        """Build a WorkflowDecision from a matched rule."""
        action = rule.get("action", "respond")
        
        decision = WorkflowDecision(
            workflow_id=workflow.get("workflow_name", "unknown"),
            next_action=action,
            policy_applied=[rule.get("policy_applied", "matched_rule")]
        )
        
        if action == "respond":
            decision.response_template = rule.get("response_template", "")
        elif action == "call_tool":
            decision.tool_plan = [rule.get("tool_name")] if rule.get("tool_name") else []
        elif action == "escalate":
            decision.escalation_reason = rule.get("escalation_reason", "Policy requires escalation")
        elif action == "route_to_workflow":
            decision.target_workflow = rule.get("target_workflow")
        elif action == "ask_clarifying":
            decision.required_fields_missing = rule.get("required_fields_missing", [])
        
        return decision.to_dict()


# Create global instance (will look for workflows/ directory)
workflow_engine = WorkflowEngine()
