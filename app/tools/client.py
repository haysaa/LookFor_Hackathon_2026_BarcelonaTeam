"""
ToolsClient - Centralized tool execution with retry logic and JSON Schema validation.
All tool calls go through here for consistent handling and tracing.
"""
import json
import httpx
import os
from typing import Any, Optional
from pathlib import Path
from app.trace import TraceLogger

# Try to import jsonschema, fall back to basic validation if not available
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class ToolsClient:
    """
    Centralized tool execution client.
    
    Features:
    - Single entry point for all tool calls
    - JSON Schema validation BEFORE calling tools
    - Automatic retry on transient failures (1 retry)
    - Normalized response format: {success: bool, data: {}, error: ""}
    - Automatic trace logging
    """
    
    def __init__(self, catalog_path: str = "tools/catalog.json"):
        self.catalog: dict[str, dict] = {}
        # Configure via env vars
        self.mock_mode = os.getenv("USE_MOCK_TOOLS", "true").lower() == "true"
        self.base_url = os.getenv("TOOLS_API_URL", "https://lookfor-backend.ngrok.app/v1/api").rstrip("/")
        self._load_catalog(catalog_path)
    
    def _load_catalog(self, path: str):
        """Load tool catalog from JSON file."""
        catalog_file = Path(path)
        if catalog_file.exists():
            try:
                with open(catalog_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    # Filter out metadata fields (version, description)
                    self.catalog = {
                        k: v for k, v in raw.items() 
                        if isinstance(v, dict) and "handle" in v
                    }
            except Exception as e:
                print(f"Error loading tool catalog: {e}")
    
    def validate_params(self, tool_name: str, params: dict) -> tuple[bool, str]:
        """
        Validate params against tool's JSON Schema.
        
        Returns:
            (is_valid, error_message)
        """
        tool_config = self.catalog.get(tool_name)
        if not tool_config:
            return False, f"Tool not in catalog: {tool_name}"
        
        schema = tool_config.get("paramsJsonSchema")
        if not schema:
            # No schema defined, allow all params
            return True, ""
        
        if HAS_JSONSCHEMA:
            try:
                jsonschema.validate(params, schema)
                return True, ""
            except jsonschema.ValidationError as e:
                return False, f"Param validation failed: {e.message}"
        else:
            # Fallback: check required fields
            required = schema.get("required", [])
            missing = [f for f in required if f not in params]
            if missing:
                return False, f"Missing required params: {missing}"
            return True, ""
    
    def execute(
        self,
        session_id: str,
        tool_name: str,
        params: dict[str, Any],
        max_retries: int = 1,
        skip_validation: bool = False
    ) -> dict[str, Any]:
        """
        Execute a tool with retry logic.
        
        Args:
            session_id: Session ID for trace logging
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool
            max_retries: Maximum number of retries on failure (default: 1)
            skip_validation: Skip JSON Schema validation (default: False)
        
        Returns:
            Normalized response: {success: bool, data: {...}, error: "..."}
        """
        # Step 1: Validate params against JSON Schema
        if not skip_validation:
            is_valid, error_msg = self.validate_params(tool_name, params)
            if not is_valid:
                TraceLogger.log_tool_call(
                    session_id=session_id,
                    tool_name=tool_name,
                    params=params,
                    response={"error": error_msg},
                    success=False,
                    retry_count=0
                )
                return {
                    "success": False,
                    "data": {},
                    "error": error_msg,
                    "should_escalate": False
                }
        
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                if self.mock_mode:
                    response = self._mock_execute(tool_name, params)
                else:
                    response = self._http_execute(tool_name, params)
                
                # Normalize response
                normalized = self._normalize_response(response)
                
                # Log to trace
                TraceLogger.log_tool_call(
                    session_id=session_id,
                    tool_name=tool_name,
                    params=params,
                    response=normalized,
                    success=normalized.get("success", False),
                    retry_count=retry_count
                )
                
                if normalized.get("success"):
                    return normalized
                
                # If not successful, retry
                last_error = normalized.get("error", "Unknown error")
                retry_count += 1
                
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                
                # Log failed attempt
                TraceLogger.log_tool_call(
                    session_id=session_id,
                    tool_name=tool_name,
                    params=params,
                    response={"error": last_error},
                    success=False,
                    retry_count=retry_count
                )
        
        # All retries exhausted
        return {
            "success": False,
            "data": {},
            "error": f"Tool failed after {max_retries + 1} attempts: {last_error}",
            "should_escalate": True
        }
    
    def _mock_execute(self, tool_name: str, params: dict) -> dict:
        """Execute tool in mock mode (for hackathon demo)."""
        
        # Deterministic failure for testing: #INVALID_FOR_TEST order ID
        order_id = params.get("order_id", "")
        if "INVALID_FOR_TEST" in str(order_id).upper():
            return {
                "success": False,
                "data": {},
                "error": "Order not found: invalid order ID or order does not exist",
                "should_escalate": True
            }
        
        # Check catalog for mock_response first
        tool_config = self.catalog.get(tool_name)
        if tool_config and "mock_response" in tool_config:
            mock = tool_config["mock_response"].copy()
            # Inject params into mock response data if applicable
            if mock.get("data"):
                if "order_id" in params and "order_id" in str(mock["data"]):
                    mock["data"]["order_id"] = params["order_id"]
            return mock
        
        # Legacy mock responses (backwards compatibility)
        mock_responses = {
            "check_order_status": {
                "success": True,
                "data": {
                    "order_id": params.get("order_id", "ORD-UNKNOWN"),
                    "status": "in_transit",
                    "carrier": "Yurtiçi Kargo",
                    "estimated_delivery": "2026-02-08",
                    "last_update": "Dağıtıma çıktı"
                }
            },
            "get_shipping_info": {
                "success": True,
                "data": {
                    "tracking_number": "YK123456789",
                    "carrier": "Yurtiçi Kargo",
                    "status": "in_transit",
                    "events": [
                        {"date": "2026-02-05", "event": "Kargoya verildi"},
                        {"date": "2026-02-06", "event": "Dağıtıma çıktı"}
                    ]
                }
            },
            "issue_store_credit": {
                "success": True,
                "data": {
                    "credit_id": "SC-123456",
                    "amount": params.get("amount", 100),
                    "bonus": params.get("bonus_percent", 10),
                    "total_credit": params.get("amount", 100) * 1.1,
                    "expires_at": "2026-05-06"
                }
            },
            "process_refund": {
                "success": True,
                "data": {
                    "refund_id": "RF-123456",
                    "amount": params.get("amount", 100),
                    "method": "original_payment",
                    "estimated_days": 5
                }
            },
            "create_reship": {
                "success": False,
                "error": "Reship requires manual approval",
                "should_escalate": True
            }
        }
        
        return mock_responses.get(tool_name, {
            "success": False,
            "error": f"Unknown tool: {tool_name}"
        })
    
    def _http_execute(self, tool_name: str, params: dict) -> dict:
        """Execute tool via HTTP (for real tool endpoints)."""
        tool_config = self.catalog.get(tool_name)
        if not tool_config:
            return {"success": False, "error": f"Tool not in catalog: {tool_name}"}
        
        endpoint = tool_config.get("endpoint")
        
        # URL Construction
        if endpoint:
            url = f"{self.base_url}{endpoint}"
        else:
            # Fallback: use tool name as endpoint if catalog is null
            url = f"{self.base_url}/{tool_name}"

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            return {"success": False, "error": str(e)}
    
    def _normalize_response(self, response: dict) -> dict:
        """Ensure response has standard format."""
        return {
            "success": response.get("success", False),
            "data": response.get("data", {}),
            "error": response.get("error", ""),
            "should_escalate": response.get("should_escalate", False)
        }
    
    def get_available_tools(self) -> list[str]:
        """Get list of available tool handles."""
        return list(self.catalog.keys())


# Global instance
tools_client = ToolsClient()
