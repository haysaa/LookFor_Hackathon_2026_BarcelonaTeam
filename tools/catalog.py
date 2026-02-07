"""
Tool Catalog
Version: 2.0 - Official Hackathon Spec
Developer: Dev B

Registry of all 18 official hackathon tools with exact specifications.
All endpoints use: {API_URL}/hackathon/{endpoint_name}
All methods are POST with JSON body.
"""

# Official Tool Catalog - 18 Tools (13 Shopify + 5 Skio)
TOOL_CATALOG = {
    # ==================== SHOPIFY TOOLS ====================
    
    "shopify_add_tags": {
        "name": "shopify_add_tags",
        "description": "Add tags to an order, a draft order, a customer, a product, or an online store article.",
        "endpoint": "/hackathon/add_tags",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["id", "tags"],
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Shopify resource GID."
                },
                "tags": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                    "description": "Tags to add."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_cancel_order": {
        "name": "shopify_cancel_order",
        "description": "Cancel an order based on order ID and reason.",
        "endpoint": "/hackathon/cancel_order",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["orderId", "reason", "notifyCustomer", "restock", "staffNote", "refundMode", "storeCredit"],
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "Order GID."
                },
                "reason": {
                    "type": "string",
                    "enum": ["CUSTOMER", "DECLINED", "FRAUD", "INVENTORY", "OTHER", "STAFF"],
                    "description": "Cancellation reason."
                },
                "notifyCustomer": {
                    "type": "boolean",
                    "default": True,
                    "description": "Notify customer."
                },
                "restock": {
                    "type": "boolean",
                    "default": True,
                    "description": "Restock inventory where applicable."
                },
                "staffNote": {
                    "type": "string",
                    "maxLength": 255,
                    "description": "Internal note."
                },
                "refundMode": {
                    "type": "string",
                    "enum": ["ORIGINAL", "STORE_CREDIT"],
                    "description": "Refund method."
                },
                "storeCredit": {
                    "type": "object",
                    "required": ["expiresAt"],
                    "description": "Store credit options (only when refundMode=STORE_CREDIT).",
                    "properties": {
                        "expiresAt": {
                            "type": ["string", "null"],
                            "description": "ISO 8601 timestamp or null for no expiry."
                        }
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_create_discount_code": {
        "name": "shopify_create_discount_code",
        "description": "Create a discount code for the customer.",
        "endpoint": "/hackathon/create_discount_code",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["type", "value", "duration", "productIds"],
            "properties": {
                "type": {
                    "type": "string",
                    "description": "'percentage' (0–1) or 'fixed' (absolute amount)."
                },
                "value": {
                    "type": "number",
                    "description": "If percentage, 0–1; if fixed, currency amount."
                },
                "duration": {
                    "type": "number",
                    "description": "Validity duration in hours (e.g. 48)."
                },
                "productIds": {
                    "type": "array",
                    "description": "Optional array of product/variant GIDs (empty for order-wide).",
                    "items": {"type": "string"}
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_create_return": {
        "name": "shopify_create_return",
        "description": "Create a Return using Shopify's returnCreate API.",
        "endpoint": "/hackathon/create_return",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["orderId"],
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "Order GID (e.g., 'gid://shopify/Order/5531567751245')."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_create_store_credit": {
        "name": "shopify_create_store_credit",
        "description": "Credit store credit to a customer or StoreCreditAccount.",
        "endpoint": "/hackathon/create_store_credit",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["id", "creditAmount", "expiresAt"],
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Customer GID or StoreCreditAccount GID (e.g. gid://shopify/Customer/7424155189325)."
                },
                "creditAmount": {
                    "type": "object",
                    "required": ["amount", "currencyCode"],
                    "properties": {
                        "amount": {
                            "type": "string",
                            "description": "Decimal amount, e.g. '49.99'."
                        },
                        "currencyCode": {
                            "type": "string",
                            "description": "ISO 4217 code, e.g. USD, EUR."
                        }
                    },
                    "additionalProperties": False
                },
                "expiresAt": {
                    "type": ["string", "null"],
                    "description": "Optional ISO8601 expiry (or null)."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_get_collection_recommendations": {
        "name": "shopify_get_collection_recommendations",
        "description": "Generate collection recommendations based on text queries.",
        "endpoint": "/hackathon/get_collection_recommendations",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["queryKeys"],
            "properties": {
                "queryKeys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords describing what the customer wants."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_get_customer_orders": {
        "name": "shopify_get_customer_orders",
        "description": "Get customer orders.",
        "endpoint": "/hackathon/get_customer_orders",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["email", "after", "limit"],
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Customer email."
                },
                "after": {
                    "type": "string",
                    "description": "Cursor to start from, \"null\" if first page"
                },
                "limit": {
                    "type": "number",
                    "description": "Number of orders to return, max 250"
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_get_order_details": {
        "name": "shopify_get_order_details",
        "description": "Fetch detailed information for a single order by ID. If user provides only the order number, use #{order_number}.",
        "endpoint": "/hackathon/get_order_details",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["orderId"],
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "Order identifier. Must start with '#', e.g. '#1234'."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_get_product_details": {
        "name": "shopify_get_product_details",
        "description": "Retrieve product information by product ID, name, or key feature.",
        "endpoint": "/hackathon/get_product_details",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["queryType", "queryKey"],
            "properties": {
                "queryKey": {
                    "type": "string",
                    "description": "Lookup key. If queryType is 'id', it must be a Shopify Product GID."
                },
                "queryType": {
                    "type": "string",
                    "enum": ["id", "name", "key feature"],
                    "description": "How to interpret queryKey."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_get_product_recommendations": {
        "name": "shopify_get_product_recommendations",
        "description": "Generate product recommendations based on keyword intents.",
        "endpoint": "/hackathon/get_product_recommendations",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["queryKeys"],
            "properties": {
                "queryKeys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords describing the customer's intent and constraints."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_get_related_knowledge_source": {
        "name": "shopify_get_related_knowledge_source",
        "description": "Retrieve related FAQs, PDFs, blog articles, and Shopify pages based on a question and optional product context.",
        "endpoint": "/hackathon/get_related_knowledge_source",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["question", "specificToProductId"],
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Customer question/problem to answer."
                },
                "specificToProductId": {
                    "type": "string",
                    "description": "Related product ID (Shopify GID) or null if not product-specific."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_refund_order": {
        "name": "shopify_refund_order",
        "description": "Refund an order.",
        "endpoint": "/hackathon/refund_order",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["orderId", "refundMethod"],
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "Order GID (e.g., 'gid://shopify/Order/5531567751245')."
                },
                "refundMethod": {
                    "type": "string",
                    "enum": ["ORIGINAL_PAYMENT_METHODS", "STORE_CREDIT"],
                    "description": "Where the refund goes."
                }
            },
            "additionalProperties": False
        }
    },
    
    "shopify_update_order_shipping_address": {
        "name": "shopify_update_order_shipping_address",
        "description": "Update an order's shipping address (Shopify orderUpdate).",
        "endpoint": "/hackathon/update_order_shipping_address",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["orderId", "shippingAddress"],
            "properties": {
                "orderId": {
                    "type": "string",
                    "description": "Order GID."
                },
                "shippingAddress": {
                    "type": "object",
                    "required": ["firstName", "lastName", "company", "address1", "address2", "city", "provinceCode", "country", "zip", "phone"],
                    "properties": {
                        "firstName": {"type": "string"},
                        "lastName": {"type": "string"},
                        "company": {"type": "string"},
                        "address1": {"type": "string"},
                        "address2": {"type": "string"},
                        "city": {"type": "string"},
                        "provinceCode": {"type": "string"},
                        "country": {"type": "string"},
                        "zip": {"type": "string"},
                        "phone": {"type": "string"}
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }
    },
    
    # ==================== SKIO TOOLS ====================
    
    "skio_cancel_subscription": {
        "name": "skio_cancel_subscription",
        "description": "Cancels the subscription if client encounter any technical errors.",
        "endpoint": "/hackathon/cancel-subscription",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["subscriptionId", "cancellationReasons"],
            "properties": {
                "subscriptionId": {
                    "type": "string",
                    "description": "ID of the subscription to be cancelled."
                },
                "cancellationReasons": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reasons of cancellation."
                }
            },
            "additionalProperties": False
        }
    },
    
    "skio_get_subscription_status": {
        "name": "skio_get_subscription_status",
        "description": "Gets the subscription status of a customer.",
        "endpoint": "/hackathon/get-subscriptions",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["email"],
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Email of the user whose subscription information is retrieved"
                }
            },
            "additionalProperties": False
        }
    },
    
    "skio_pause_subscription": {
        "name": "skio_pause_subscription",
        "description": "Pauses the subscription.",
        "endpoint": "/hackathon/pause-subscription",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["subscriptionId", "pausedUntil"],
            "properties": {
                "subscriptionId": {
                    "type": "string",
                    "description": "ID of the subscription to be paused."
                },
                "pausedUntil": {
                    "type": "string",
                    "description": "Date to pause the subscription until. Format: YYYY-MM-DD"
                }
            },
            "additionalProperties": False
        }
    },
    
    "skio_skip_next_order_subscription": {
        "name": "skio_skip_next_order_subscription",
        "description": "Skips the next order of an ongoing subscription.",
        "endpoint": "/hackathon/skip-next-order-subscription",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["subscriptionId"],
            "properties": {
                "subscriptionId": {
                    "type": "string",
                    "description": "ID of the subscription to be skipped."
                }
            },
            "additionalProperties": False
        }
    },
    
    "skio_unpause_subscription": {
        "name": "skio_unpause_subscription",
        "description": "Unpauses the paused subscription.",
        "endpoint": "/hackathon/unpause-subscription",
        "method": "POST",
        "paramsJsonSchema": {
            "type": "object",
            "required": ["subscriptionId"],
            "properties": {
                "subscriptionId": {
                    "type": "string",
                    "description": "ID of the subscription to be unpaused."
                }
            },
            "additionalProperties": False
        }
    }
}


# Helper functions
def get_tool(tool_name: str) -> dict:
    """Get tool definition by name."""
    return TOOL_CATALOG.get(tool_name)


def list_tools() -> list:
    """List all available tool names."""
    return list(TOOL_CATALOG.keys())


def get_tool_schema(tool_name: str) -> dict:
    """Get the parameter schema for a tool (paramsJsonSchema)."""
    tool = get_tool(tool_name)
    return tool.get("paramsJsonSchema", {}) if tool else {}


def get_tool_endpoint(tool_name: str) -> str:
    """Get the endpoint for a tool."""
    tool = get_tool(tool_name)
    return tool.get("endpoint", "") if tool else ""


def get_tool_method(tool_name: str) -> str:
    """Get the HTTP method for a tool."""
    tool = get_tool(tool_name)
    return tool.get("method", "POST") if tool else "POST"
