"""
Workflow Decision Schema
Version: 1.0
Developer: Dev B

Defines the output schema from WorkflowEngine.
This is the contract between WorkflowEngine (Dev A) and downstream agents.
"""
from typing import Optional, List, Literal, Any
from pydantic import BaseModel, Field


class ToolPlan(BaseModel):
    """A single tool to be executed."""
    tool_name: str = Field(
        ...,
        description="Name of the tool from catalog"
    )
    params: dict = Field(
        default_factory=dict,
        description="Parameters to pass to the tool"
    )


class WorkflowDecision(BaseModel):
    """
    Output schema from the deterministic WorkflowEngine.
    
    The WorkflowEngine evaluates JSON decision trees and produces
    this structured decision for the Orchestrator to act upon.
    """
    workflow_id: str = Field(
        ...,
        description="ID of the workflow being executed (WISMO, WRONG_MISSING, REFUND_STANDARD)"
    )
    next_action: Literal["ask_clarifying", "call_tool", "respond", "escalate", "route_to_workflow"] = Field(
        ...,
        description="Next action for the orchestrator to take"
    )
    target_workflow: Optional[str] = Field(
        None,
        description="If next_action is route_to_workflow, which workflow to route to"
    )
    required_fields_missing: List[str] = Field(
        default_factory=list,
        description="List of fields that need to be collected from customer"
    )
    policy_applied: List[str] = Field(
        default_factory=list,
        description="List of policy rules that were applied in this decision"
    )
    tool_plan: List[ToolPlan] = Field(
        default_factory=list,
        description="Tools to execute if next_action is call_tool"
    )
    response_template: Optional[str] = Field(
        None,
        description="Template for respond action"
    )
    escalation_reason: Optional[str] = Field(
        None,
        description="Reason for escalation if next_action is escalate"
    )
    clarifying_questions: List[str] = Field(
        default_factory=list,
        description="Questions to ask if next_action is ask_clarifying"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "WISMO",
                "next_action": "respond",
                "required_fields_missing": [],
                "policy_applied": ["friday_promise"],
                "tool_plan": [],
                "response_template": "Your order will arrive by Friday"
            }
        }
