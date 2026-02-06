"""
Triage Agent Schema
Version: 1.0
Developer: Dev B

Defines the strict JSON output schema for the Triage Agent.
Used for intent classification and entity extraction.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class Intent(str, Enum):
    """Supported intent types for triage classification."""
    WISMO = "WISMO"  # Where Is My Order
    REFUND_STANDARD = "REFUND_STANDARD"
    WRONG_MISSING = "WRONG_MISSING"
    UNKNOWN = "UNKNOWN"


class ExtractedEntities(BaseModel):
    """Entities extracted from customer message."""
    order_id: Optional[str] = Field(
        None,
        description="Order ID extracted from message (e.g., #12345, ORD-12345)"
    )
    tracking_number: Optional[str] = Field(
        None,
        description="Shipping tracking number if mentioned"
    )
    item_name: Optional[str] = Field(
        None,
        description="Product name or description mentioned"
    )


class TriageResult(BaseModel):
    """
    Strict JSON output schema for Triage Agent.
    
    This schema is enforced via OpenAI's response_format parameter
    to ensure consistent structured outputs.
    """
    intent: Intent = Field(
        ...,
        description="Classified intent type"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the classification (0.0-1.0)"
    )
    entities: ExtractedEntities = Field(
        default_factory=ExtractedEntities,
        description="Extracted entities from the message"
    )
    needs_human: bool = Field(
        False,
        description="True if low confidence (<0.6) or ambiguous request"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Brief explanation of the classification decision"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "WISMO",
                "confidence": 0.92,
                "entities": {
                    "order_id": "ORD-12345",
                    "tracking_number": None,
                    "item_name": None
                },
                "needs_human": False,
                "reasoning": "Customer asking about order delivery status"
            }
        }


# JSON Schema for OpenAI structured outputs
TRIAGE_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["WISMO", "REFUND_STANDARD", "WRONG_MISSING", "UNKNOWN"]
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "entities": {
            "type": "object",
            "properties": {
                "order_id": {"type": ["string", "null"]},
                "tracking_number": {"type": ["string", "null"]},
                "item_name": {"type": ["string", "null"]}
            },
            "required": ["order_id", "tracking_number", "item_name"]
        },
        "needs_human": {"type": "boolean"},
        "reasoning": {"type": ["string", "null"]}
    },
    "required": ["intent", "confidence", "entities", "needs_human"],
    "additionalProperties": False
}
