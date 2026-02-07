"""
Mock Tool Server
Version: 2.0 - Official Hackathon Spec
Developer: Dev B

Provides mock responses for all 18 official tools before real endpoints are available.
All responses follow the standard contract: {success: bool, data: {}, error: ""}
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random
import string


class MockToolServer:
    """
    Mock implementation of all 18 official hackathon tool endpoints.
    
    Returns realistic mock data following the official tool specification schemas.
    Set fail_rate > 0 to simulate random failures for retry testing.
    """
    
    def __init__(self, fail_rate: float = 0.0):
        """
        Initialize mock server.
        
        Args:
            fail_rate: Probability of random failure (0.0 to 1.0) for testing retries
        """
        self.fail_rate = fail_rate
        self._order_db = self._init_mock_orders()
        self._subscription_db = self._init_mock_subscriptions()
    
    def _init_mock_orders(self) -> Dict[str, dict]:
        """Initialize mock order database with Shopify GID format."""
        return {
            "#12345": {
                "id": "gid://shopify/Order/5531567751245",
                "name": "#12345",
                "createdAt": "2026-02-01T10:00:00Z",
                "status": "FULFILLED",
                "trackingUrl": "https://tracking.fedex.com/abc123"
            },
            "#54321": {
                "id": "gid://shopify/Order/5531567751246",
                "name": "#54321",
                "createdAt": "2026-01-25T14:30:00Z",
                "status": "DELIVERED",
                "trackingUrl": "https://tracking.ups.com/xyz789"
            },
            "#99999": {
                "id": "gid://shopify/Order/5531567751247",
                "name": "#99999",
                "createdAt": "2026-02-05T09:15:00Z",
                "status": "UNFULFILLED",
                "trackingUrl": None
            }
        }
    
    def _init_mock_subscriptions(self) -> Dict[str, dict]:
        """Initialize mock subscription database."""
        return {
            "customer@example.com": [
                {
                    "status": "ACTIVE",
                    "subscriptionId": "sub_124",
                    "nextBillingDate": "2026-03-01"
                },
                {
                    "status": "PAUSED",
                    "subscriptionId": "sub_123",
                    "nextBillingDate": "2026-05-01"
                }
            ]
        }
    
    def _should_fail(self) -> bool:
        """Check if this call should randomly fail."""
        return random.random() < self.fail_rate
    
    def _generate_id(self, prefix: str = "") -> str:
        """Generate a random ID."""
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}{suffix}"
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a mock tool call.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool
        
        Returns:
            Standard response: {success: bool, data: {}, error: ""}
        """
        # Simulate random failures
        if self._should_fail():
            return {
                "success": False,
                "data": {},
                "error": "Simulated transient failure for testing"
            }
        
        # Route to appropriate handler
        handlers = {
            # Shopify tools
            "shopify_add_tags": self._shopify_add_tags,
            "shopify_cancel_order": self._shopify_cancel_order,
            "shopify_create_discount_code": self._shopify_create_discount_code,
            "shopify_create_return": self._shopify_create_return,
            "shopify_create_store_credit": self._shopify_create_store_credit,
            "shopify_get_collection_recommendations": self._shopify_get_collection_recommendations,
            "shopify_get_customer_orders": self._shopify_get_customer_orders,
            "shopify_get_order_details": self._shopify_get_order_details,
            "shopify_get_product_details": self._shopify_get_product_details,
            "shopify_get_product_recommendations": self._shopify_get_product_recommendations,
            "shopify_get_related_knowledge_source": self._shopify_get_related_knowledge_source,
            "shopify_refund_order": self._shopify_refund_order,
            "shopify_update_order_shipping_address": self._shopify_update_order_shipping_address,
            # Skio tools
            "skio_cancel_subscription": self._skio_cancel_subscription,
            "skio_get_subscription_status": self._skio_get_subscription_status,
            "skio_pause_subscription": self._skio_pause_subscription,
            "skio_skip_next_order_subscription": self._skio_skip_next_order_subscription,
            "skio_unpause_subscription": self._skio_unpause_subscription
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                "success": False,
                "data": {},
                "error": f"Unknown tool: {tool_name}"
            }
        
        try:
            result = handler(params)
            return {
                "success": True,
                "data": result,
                "error": ""
            }
        except Exception as e:
            return {
                "success": False,
                "data": {},
                "error": str(e)
            }
    
    # ==================== SHOPIFY MOCK HANDLERS ====================
    
    def _shopify_add_tags(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_add_tags - always succeeds."""
        return {}
    
    def _shopify_cancel_order(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_cancel_order - always succeeds."""
        return {}
    
    def _shopify_create_discount_code(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_create_discount_code - returns discount code."""
        return {
            "code": f"DISCOUNT_LF_{self._generate_id().upper()}"
        }
    
    def _shopify_create_return(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_create_return - always succeeds."""
        return {}
    
    def _shopify_create_store_credit(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_create_store_credit - returns account info."""
        credit_amount = params.get("creditAmount", {})
        amount = credit_amount.get("amount", "0.00")
        currency = credit_amount.get("currencyCode", "USD")
        
        # Mock balance calculation (current balance + new credit)
        new_balance = float(amount) * 1.5  # Mock existing balance
        
        return {
            "storeCreditAccountId": f"gid://shopify/StoreCreditAccount/{self._generate_id()}",
            "credited": {
                "amount": amount,
                "currencyCode": currency
            },
            "newBalance": {
                "amount": f"{new_balance:.2f}",
                "currencyCode": currency
            }
        }
    
    def _shopify_get_collection_recommendations(self, params: Dict[str, Any]) -> list:
        """Mock shopify_get_collection_recommendations - returns collections."""
        return [
            {
                "id": "gid://shopify/Collection/1",
                "title": "Acne Care",
                "handle": "acne-care"
            },
            {
                "id": "gid://shopify/Collection/2",
                "title": "Sleep Aid",
                "handle": "sleep-aid"
            }
        ]
    
    def _shopify_get_customer_orders(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_get_customer_orders - returns order list."""
        return {
            "orders": [
                {
                    "id": "gid://shopify/Order/1",
                    "name": "#1001",
                    "createdAt": "2026-02-06T01:06:46Z",
                    "status": "FULFILLED",
                    "trackingUrl": "https://tracking.example.com/abc123"
                },
                {
                    "id": "gid://shopify/Order/2",
                    "name": "#1002",
                    "createdAt": "2026-01-15T14:20:00Z",
                    "status": "DELIVERED",
                    "trackingUrl": "https://tracking.example.com/def456"
                }
            ],
            "hasNextPage": False,
            "endCursor": None
        }
    
    def _shopify_get_order_details(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_get_order_details - returns order details."""
        order_id = params.get("orderId", "")
        
        # Check if we have this order in our mock DB
        if order_id in self._order_db:
            return self._order_db[order_id]
        
        # Return generic mock for unknown orders
        return {
            "id": f"gid://shopify/Order/{self._generate_id()}",
            "name": order_id,
            "createdAt": (datetime.now() - timedelta(days=3)).isoformat() + "Z",
            "status": "FULFILLED",
            "trackingUrl": f"https://tracking.example.com/{self._generate_id()}"
        }
    
    def _shopify_get_product_details(self, params: Dict[str, Any]) -> list:
        """Mock shopify_get_product_details - returns product array."""
        return [
            {
                "id": "gid://shopify/Product/9",
                "title": "Patch",
                "handle": "patch"
            }
        ]
    
    def _shopify_get_product_recommendations(self, params: Dict[str, Any]) -> list:
        """Mock shopify_get_product_recommendations - returns product array."""
        return [
            {
                "id": "gid://shopify/Product/9",
                "title": "Patch",
                "handle": "patch"
            },
            {
                "id": "gid://shopify/Product/10",
                "title": "Sleep Strips",
                "handle": "sleep-strips"
            }
        ]
    
    def _shopify_get_related_knowledge_source(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_get_related_knowledge_source - returns knowledge sources."""
        return {
            "faqs": [],
            "pdfs": [],
            "blogArticles": [],
            "pages": []
        }
    
    def _shopify_refund_order(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_refund_order - always succeeds."""
        return {}
    
    def _shopify_update_order_shipping_address(self, params: Dict[str, Any]) -> dict:
        """Mock shopify_update_order_shipping_address - always succeeds."""
        return {}
    
    # ==================== SKIO MOCK HANDLERS ====================
    
    def _skio_cancel_subscription(self, params: Dict[str, Any]) -> dict:
        """Mock skio_cancel_subscription - always succeeds."""
        return {}
    
    def _skio_get_subscription_status(self, params: Dict[str, Any]) -> list:
        """Mock skio_get_subscription_status - returns subscriptions."""
        email = params.get("email", "")
        
        # Check if we have subscriptions for this customer
        if email in self._subscription_db:
            return self._subscription_db[email]
        
        # Return mock subscription
        return [
            {
                "status": "ACTIVE",
                "subscriptionId": f"sub_{self._generate_id()}",
                "nextBillingDate": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            }
        ]
    
    def _skio_pause_subscription(self, params: Dict[str, Any]) -> dict:
        """Mock skio_pause_subscription - always succeeds."""
        return {}
    
    def _skio_skip_next_order_subscription(self, params: Dict[str, Any]) -> dict:
        """Mock skio_skip_next_order_subscription - always succeeds."""
        return {}
    
    def _skio_unpause_subscription(self, params: Dict[str, Any]) -> dict:
        """Mock skio_unpause_subscription - always succeeds."""
        return {}


# Global mock server instance
_mock_server: Optional[MockToolServer] = None


def get_mock_server(fail_rate: float = 0.0) -> MockToolServer:
    """Get or create the global mock server instance."""
    global _mock_server
    if _mock_server is None:
        _mock_server = MockToolServer(fail_rate=fail_rate)
    return _mock_server
