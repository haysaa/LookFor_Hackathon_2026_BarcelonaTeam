"""
Tool Catalog
Version: 1.0
Developer: Dev B

Registry of available tools with their schemas and endpoints.
This is a stub that will be updated with real endpoints during hackathon.
"""

TOOL_CATALOG = {
    "check_order_status": {
        "name": "check_order_status",
        "description": "Check the status of an order by order ID",
        "endpoint": "/api/orders/{order_id}/status",
        "method": "GET",
        "params_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to check"
                }
            },
            "required": ["order_id"]
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "processing", "shipped", "delivered", "cancelled"]},
                "order_date": {"type": "string"},
                "shipping_carrier": {"type": "string"},
                "tracking_number": {"type": "string"},
                "estimated_delivery": {"type": "string"}
            }
        }
    },
    "get_shipping_info": {
        "name": "get_shipping_info",
        "description": "Get detailed shipping and tracking information",
        "endpoint": "/api/shipping/{tracking_number}",
        "method": "GET",
        "params_schema": {
            "type": "object",
            "properties": {
                "tracking_number": {
                    "type": "string",
                    "description": "Shipping tracking number"
                }
            },
            "required": ["tracking_number"]
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "tracking_number": {"type": "string"},
                "carrier": {"type": "string"},
                "current_status": {"type": "string"},
                "last_location": {"type": "string"},
                "estimated_delivery": {"type": "string"},
                "delivery_attempts": {"type": "integer"}
            }
        }
    },
    "issue_store_credit": {
        "name": "issue_store_credit",
        "description": "Issue store credit to customer with optional bonus percentage",
        "endpoint": "/api/credits/issue",
        "method": "POST",
        "params_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "amount": {"type": "number"},
                "bonus_percent": {"type": "number", "default": 0},
                "reason": {"type": "string"}
            },
            "required": ["customer_id", "amount", "reason"]
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "credit_id": {"type": "string"},
                "customer_id": {"type": "string"},
                "total_amount": {"type": "number"},
                "expires_at": {"type": "string"}
            }
        }
    },
    "process_refund": {
        "name": "process_refund",
        "description": "Process a cash refund for an order",
        "endpoint": "/api/refunds/process",
        "method": "POST",
        "params_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
                "reason": {"type": "string"},
                "refund_method": {"type": "string", "enum": ["original_payment", "bank_transfer"]}
            },
            "required": ["order_id", "reason"]
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "refund_id": {"type": "string"},
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
                "status": {"type": "string"},
                "estimated_processing_days": {"type": "integer"}
            }
        }
    },
    "request_reship": {
        "name": "request_reship",
        "description": "Request a reship of items (requires human approval)",
        "endpoint": "/api/orders/{order_id}/reship",
        "method": "POST",
        "params_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "items": {"type": "array", "items": {"type": "string"}},
                "reason": {"type": "string"}
            },
            "required": ["order_id", "reason"]
        },
        "response_schema": {
            "type": "object",
            "properties": {
                "reship_request_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending_approval", "approved", "rejected"]},
                "requires_manual_review": {"type": "boolean"}
            }
        },
        "notes": "Reship requests typically require human approval and will escalate"
    }
}


def get_tool(tool_name: str) -> dict:
    """Get tool definition by name."""
    return TOOL_CATALOG.get(tool_name)


def list_tools() -> list:
    """List all available tool names."""
    return list(TOOL_CATALOG.keys())


def get_tool_schema(tool_name: str) -> dict:
    """Get the parameter schema for a tool."""
    tool = get_tool(tool_name)
    return tool.get("params_schema", {}) if tool else {}
