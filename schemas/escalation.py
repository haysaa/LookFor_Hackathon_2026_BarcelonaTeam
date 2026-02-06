"""
Escalation Schema
Version: 1.0
Developer: Dev B

Strict JSON schema for internal escalation tickets.
This is a REQUIRED format per the sprint plan requirements.
"""
from typing import List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class EscalationTicket(BaseModel):
    """
    Internal escalation ticket schema.
    
    CRITICAL: This schema is mandated by requirements and must match exactly:
    - escalation_id: "esc_xxx" format
    - customer_id: "cust_XXXXXXXX" format
    - priority: low|medium|high only
    - created_at: ISO-8601 format
    """
    escalation_id: str = Field(
        ...,
        pattern=r"^esc_[a-zA-Z0-9]+$",
        description="Unique escalation ID in format esc_xxx"
    )
    customer_id: str = Field(
        ...,
        pattern=r"^cust_[a-zA-Z0-9]+$",
        description="Customer ID in format cust_XXXXXXXX"
    )
    reason: str = Field(
        ...,
        min_length=1,
        description="Human-readable reason for escalation"
    )
    conversation_summary: str = Field(
        ...,
        min_length=1,
        description="Brief summary of the conversation leading to escalation"
    )
    attempted_actions: List[str] = Field(
        default_factory=list,
        description="List of actions attempted before escalation"
    )
    priority: Literal["low", "medium", "high"] = Field(
        ...,
        description="Escalation priority level"
    )
    created_at: str = Field(
        ...,
        description="ISO-8601 timestamp of escalation creation"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "escalation_id": "esc_abc123",
                "customer_id": "cust_12345678",
                "reason": "Delivery promise exceeded, customer frustrated",
                "conversation_summary": "Customer contacted about delayed order #12345. Promise made for Friday delivery but still not received.",
                "attempted_actions": [
                    "check_order_status",
                    "get_shipping_info",
                    "friday_promise_given"
                ],
                "priority": "high",
                "created_at": "2026-02-06T16:00:00Z"
            }
        }


class CustomerEscalationEmail(BaseModel):
    """Customer-facing escalation email content."""
    subject: str = Field(
        ...,
        description="Email subject line"
    )
    body: str = Field(
        ...,
        description="Email body content"
    )


class EscalationOutput(BaseModel):
    """
    Complete output from Escalation Agent.
    Contains both customer email and internal ticket.
    """
    customer_email: CustomerEscalationEmail
    escalation_ticket: EscalationTicket


# JSON Schema for validation
ESCALATION_TICKET_SCHEMA = {
    "type": "object",
    "properties": {
        "escalation_id": {
            "type": "string",
            "pattern": "^esc_[a-zA-Z0-9]+$"
        },
        "customer_id": {
            "type": "string",
            "pattern": "^cust_[a-zA-Z0-9]+$"
        },
        "reason": {"type": "string", "minLength": 1},
        "conversation_summary": {"type": "string", "minLength": 1},
        "attempted_actions": {
            "type": "array",
            "items": {"type": "string"}
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high"]
        },
        "created_at": {"type": "string"}
    },
    "required": [
        "escalation_id",
        "customer_id", 
        "reason",
        "conversation_summary",
        "attempted_actions",
        "priority",
        "created_at"
    ],
    "additionalProperties": False
}
