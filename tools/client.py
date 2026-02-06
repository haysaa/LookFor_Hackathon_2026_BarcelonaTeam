"""
Tools Client
Version: 1.0
Developer: Dev B

Unified client for executing tools with retry logic, normalization, and tracing.
All tool calls go through this client for consistent behavior.
"""
import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from .catalog import get_tool, get_tool_schema
from .mock_server import get_mock_server


@dataclass
class ToolCallResult:
    """Result of a tool execution."""
    tool_name: str
    params: Dict[str, Any]
    success: bool
    data: Dict[str, Any]
    error: str = ""
    retry_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    should_escalate: bool = False


class ToolsClient:
    """
    Unified tools client with:
    - Single entry point for all tool calls
    - Automatic retry on transient failures
    - Response normalization
    - Trace event generation
    - Escalation flagging on persistent failures
    
    Contract: All responses are normalized to:
    {
        "success": true/false,
        "data": {...},
        "error": "..."
    }
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        use_mock: bool = True,
        max_retries: int = 1,
        timeout: int = 10,
        mock_fail_rate: float = 0.0
    ):
        """
        Initialize ToolsClient.
        
        Args:
            base_url: Base URL for real tool endpoints (when not using mock)
            use_mock: If True, use mock server instead of real endpoints
            max_retries: Number of retries on failure (default: 1)
            timeout: Request timeout in seconds
            mock_fail_rate: For testing - probability of mock failures
        """
        self.base_url = base_url or os.getenv("TOOLS_API_URL", "http://localhost:8001")
        self.use_mock = use_mock
        self.max_retries = max_retries
        self.timeout = timeout
        
        if use_mock:
            self.mock_server = get_mock_server(fail_rate=mock_fail_rate)
        
        # Track all calls for tracing
        self.call_history: List[ToolCallResult] = []
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolCallResult:
        """
        Execute a tool with retry logic.
        
        Args:
            tool_name: Name of the tool from catalog
            params: Parameters for the tool
        
        Returns:
            ToolCallResult with success status, data, and metadata
        """
        tool_def = get_tool(tool_name)
        if not tool_def:
            result = ToolCallResult(
                tool_name=tool_name,
                params=params,
                success=False,
                data={},
                error=f"Tool not found in catalog: {tool_name}",
                should_escalate=True
            )
            self.call_history.append(result)
            return result
        
        # Execute with retry
        last_error = ""
        retry_count = 0
        
        for attempt in range(self.max_retries + 1):
            try:
                if self.use_mock:
                    response = self.mock_server.execute(tool_name, params)
                else:
                    response = self._execute_real(tool_def, params)
                
                if response.get("success", False):
                    result = ToolCallResult(
                        tool_name=tool_name,
                        params=params,
                        success=True,
                        data=response.get("data", {}),
                        retry_count=retry_count
                    )
                    self.call_history.append(result)
                    return result
                
                # Failed but got response
                last_error = response.get("error", "Unknown error")
                retry_count = attempt + 1
                
            except Exception as e:
                last_error = str(e)
                retry_count = attempt + 1
        
        # All retries exhausted
        result = ToolCallResult(
            tool_name=tool_name,
            params=params,
            success=False,
            data={},
            error=last_error,
            retry_count=retry_count,
            should_escalate=True  # Flag for escalation after max retries
        )
        self.call_history.append(result)
        return result
    
    def _execute_real(self, tool_def: dict, params: Dict[str, Any]) -> dict:
        """Execute a real HTTP call to tool endpoint."""
        endpoint = tool_def.get("endpoint", "")
        method = tool_def.get("method", "GET").upper()
        
        # Build URL with path params
        url = self.base_url + endpoint
        for key, value in params.items():
            url = url.replace(f"{{{key}}}", str(value))
        
        try:
            if method == "GET":
                resp = requests.get(url, params=params, timeout=self.timeout)
            elif method == "POST":
                resp = requests.post(url, json=params, timeout=self.timeout)
            else:
                return {"success": False, "data": {}, "error": f"Unsupported method: {method}"}
            
            # Normalize response
            if resp.status_code == 200:
                data = resp.json()
                # Handle if API already returns our format
                if "success" in data:
                    return data
                # Wrap raw response
                return {"success": True, "data": data, "error": ""}
            else:
                return {
                    "success": False,
                    "data": {},
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}"
                }
                
        except requests.Timeout:
            return {"success": False, "data": {}, "error": "Request timeout"}
        except requests.RequestException as e:
            return {"success": False, "data": {}, "error": str(e)}
    
    def execute_plan(self, tool_plan: List[Dict[str, Any]]) -> List[ToolCallResult]:
        """
        Execute a list of tools from a workflow tool plan.
        
        Args:
            tool_plan: List of {tool_name, params} dicts
        
        Returns:
            List of ToolCallResults
        """
        results = []
        for item in tool_plan:
            result = self.execute(
                tool_name=item.get("tool_name", ""),
                params=item.get("params", {})
            )
            results.append(result)
            
            # Stop on failure that requires escalation
            if result.should_escalate:
                break
        
        return results
    
    def to_trace_events(self, results: Optional[List[ToolCallResult]] = None) -> List[dict]:
        """
        Convert tool results to trace events.
        
        Args:
            results: Results to convert (defaults to all history)
        
        Returns:
            List of trace event dicts
        """
        if results is None:
            results = self.call_history
        
        return [
            {
                "agent": "tools_client",
                "action": "tool_call",
                "data": {
                    "tool_name": r.tool_name,
                    "params": r.params,
                    "success": r.success,
                    "data": r.data,
                    "error": r.error,
                    "retry_count": r.retry_count,
                    "should_escalate": r.should_escalate
                },
                "timestamp": r.timestamp
            }
            for r in results
        ]
    
    def get_last_result(self) -> Optional[ToolCallResult]:
        """Get the most recent tool call result."""
        return self.call_history[-1] if self.call_history else None
    
    def any_escalation_needed(self) -> bool:
        """Check if any tool call requires escalation."""
        return any(r.should_escalate for r in self.call_history)
    
    def clear_history(self):
        """Clear the call history."""
        self.call_history = []
