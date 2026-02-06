"""
Mock Tool Server
Version: 1.0
Developer: Dev B

Provides mock responses for tools before real endpoints are available.
All responses follow the standard contract: {success: bool, data: {}, error: ""}
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random
import string


class MockToolServer:
    """
    Mock implementation of tool endpoints for testing.
    
    Returns realistic mock data following the tool catalog schemas.
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
    
    def _init_mock_orders(self) -> Dict[str, dict]:
        """Initialize mock order database."""
        return {
            "12345": {
                "order_id": "12345",
                "status": "shipped",
                "order_date": "2026-02-01",
                "shipping_carrier": "FedEx",
                "tracking_number": "FX123456789",
                "estimated_delivery": "2026-02-07",
                "customer_id": "cust_abc123",
                "total_amount": 99.99
            },
            "54321": {
                "order_id": "54321",
                "status": "delivered",
                "order_date": "2026-01-25",
                "shipping_carrier": "UPS",
                "tracking_number": "UP987654321",
                "estimated_delivery": "2026-01-30",
                "customer_id": "cust_xyz789",
                "total_amount": 149.99
            },
            "99999": {
                "order_id": "99999",
                "status": "processing",
                "order_date": "2026-02-05",
                "shipping_carrier": None,
                "tracking_number": None,
                "estimated_delivery": "2026-02-10",
                "customer_id": "cust_test001",
                "total_amount": 49.99
            }
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
            "check_order_status": self._check_order_status,
            "get_shipping_info": self._get_shipping_info,
            "issue_store_credit": self._issue_store_credit,
            "process_refund": self._process_refund,
            "request_reship": self._request_reship
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
    
    def _check_order_status(self, params: Dict[str, Any]) -> dict:
        """Mock check_order_status tool."""
        order_id = params.get("order_id", "").replace("#", "").replace("ORD-", "")
        
        if order_id in self._order_db:
            order = self._order_db[order_id]
            return {
                "order_id": order["order_id"],
                "status": order["status"],
                "order_date": order["order_date"],
                "shipping_carrier": order["shipping_carrier"],
                "tracking_number": order["tracking_number"],
                "estimated_delivery": order["estimated_delivery"]
            }
        
        # Return generic mock for unknown orders
        return {
            "order_id": order_id,
            "status": "shipped",
            "order_date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "shipping_carrier": "Standard Shipping",
            "tracking_number": f"TRK{order_id}",
            "estimated_delivery": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        }
    
    def _get_shipping_info(self, params: Dict[str, Any]) -> dict:
        """Mock get_shipping_info tool."""
        tracking = params.get("tracking_number", "")
        
        return {
            "tracking_number": tracking,
            "carrier": "FedEx",
            "current_status": "In Transit",
            "last_location": "Distribution Center, Istanbul",
            "estimated_delivery": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "delivery_attempts": 0
        }
    
    def _issue_store_credit(self, params: Dict[str, Any]) -> dict:
        """Mock issue_store_credit tool."""
        customer_id = params.get("customer_id", "unknown")
        amount = params.get("amount", 0)
        bonus = params.get("bonus_percent", 0)
        
        total = amount * (1 + bonus / 100)
        
        return {
            "credit_id": self._generate_id("cr_"),
            "customer_id": customer_id,
            "total_amount": round(total, 2),
            "expires_at": (datetime.now() + timedelta(days=365)).isoformat()
        }
    
    def _process_refund(self, params: Dict[str, Any]) -> dict:
        """Mock process_refund tool."""
        order_id = params.get("order_id", "").replace("#", "").replace("ORD-", "")
        
        # Get order amount if known
        amount = params.get("amount")
        if amount is None and order_id in self._order_db:
            amount = self._order_db[order_id]["total_amount"]
        elif amount is None:
            amount = 50.00  # Default mock amount
        
        return {
            "refund_id": self._generate_id("ref_"),
            "order_id": order_id,
            "amount": amount,
            "status": "processing",
            "estimated_processing_days": 5
        }
    
    def _request_reship(self, params: Dict[str, Any]) -> dict:
        """Mock request_reship tool - always requires approval."""
        order_id = params.get("order_id", "").replace("#", "").replace("ORD-", "")
        
        return {
            "reship_request_id": self._generate_id("rs_"),
            "status": "pending_approval",
            "requires_manual_review": True
        }


# Global mock server instance
_mock_server: Optional[MockToolServer] = None


def get_mock_server(fail_rate: float = 0.0) -> MockToolServer:
    """Get or create the global mock server instance."""
    global _mock_server
    if _mock_server is None:
        _mock_server = MockToolServer(fail_rate=fail_rate)
    return _mock_server
