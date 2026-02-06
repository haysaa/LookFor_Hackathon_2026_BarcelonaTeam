"""
ActionAgent - Executes tools based on workflow decisions
Version: 1.0
Developer: Dev B

Handles tool execution when WorkflowEngine decides next_action=call_tool.
Resolves parameter placeholders from session context and manages escalation.
"""
from typing import Dict, Any, Optional
from dataclasses import asdict

from tools.client import ToolsClient, ToolCallResult
from schemas.workflow import WorkflowDecision, ToolPlan
from schemas.session import Session, TraceEvent
from config import AUTO_ESCALATE_ON_TOOL_FAILURE, TOOL_FAILURE_THRESHOLD, get_fallback_message


class ActionAgent:
    """
    Executes tools based on workflow decisions.
    
    Responsibilities:
    1. Extract tool plan from workflow decision
    2. Resolve parameter placeholders from session context
    3. Execute tools via ToolsClient
    4. Store results in session.tool_history
    5. Generate trace events
    6. Handle escalation flags
    
    Flow:
        WorkflowEngine → decision with next_action=call_tool
        → ActionAgent.execute()
        → ToolsClient.execute()
        → Store in session
        → Return results
    """
    
    def __init__(self, tools_client: Optional[ToolsClient] = None):
        """
        Initialize ActionAgent.
        
        Args:
            tools_client: ToolsClient instance (creates default if None)
        """
        self.tools_client = tools_client or ToolsClient(use_mock=True)
    
    def execute(
        self, 
        session: Session, 
        decision: WorkflowDecision
    ) -> Dict[str, Any]:
        """
        Execute tools based on workflow decision.
        
        Args:
            session: Current session state
            decision: Workflow decision with tool_plan
        
        Returns:
            {
                "success": bool,
                "results": List[ToolCallResult],
                "should_escalate": bool,
                "error": Optional[str],
                "fallback_message": Optional[str]  # User-friendly error message
            }
        """
        if decision.next_action != "call_tool":
            return {
                "success": False,
                "results": [],
                "should_escalate": False,
                "error": f"Invalid action: {decision.next_action}, expected 'call_tool'",
                "fallback_message": get_fallback_message("general_error")
            }
        
        if not decision.tool_plan:
            return {
                "success": False,
                "results": [],
                "should_escalate": False,
                "error": "No tools specified in tool_plan",
                "fallback_message": get_fallback_message("general_error")
            }
        
        # Execute each tool in the plan
        results = []
        should_escalate = False
        failure_count = 0
        
        for tool_item in decision.tool_plan:
            # Resolve params from session context
            resolved_params = self._resolve_params(
                raw_params=tool_item.params,
                session=session
            )
            
            # Execute tool
            result = self.tools_client.execute(
                tool_name=tool_item.tool_name,
                params=resolved_params
            )
            
            results.append(result)
            
            # Update session tool_history
            tool_record = {
                "tool_name": result.tool_name,
                "params": result.params,
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "retry_count": result.retry_count,
                "timestamp": result.timestamp
            }
            session.tool_history.append(tool_record)
            
            # RISK MITIGATION: Track failures
            if not result.success:
                failure_count += 1
            
            # Check for escalation
            if result.should_escalate:
                should_escalate = True
                # Stop executing further tools
                break
        
        # RISK MITIGATION: Auto-escalate if too many failures
        if failure_count >= TOOL_FAILURE_THRESHOLD and AUTO_ESCALATE_ON_TOOL_FAILURE:
            should_escalate = True
        
        # Determine overall success
        all_success = all(r.success for r in results)
        
        # Generate user-friendly fallback message if failures occurred
        fallback_message = None
        if not all_success or should_escalate:
            if should_escalate:
                fallback_message = get_fallback_message("escalated")
            else:
                fallback_message = get_fallback_message("tool_failure")
        
        return {
            "success": all_success,
            "results": results,
            "should_escalate": should_escalate,
            "error": results[-1].error if not all_success else None,
            "fallback_message": fallback_message
        }
    
    def _resolve_params(
        self, 
        raw_params: Dict[str, Any], 
        session: Session
    ) -> Dict[str, Any]:
        """
        Replace parameter placeholders with actual values from session.
        
        Supported placeholders:
        - {order_id} → session.case_context.order_id
        - {customer_id} → session.customer_info.customer_id
        - {tracking_number} → session.case_context.tracking_number
        - {item_name} → session.case_context.item_name
        - {order_date} → session.case_context.order_date
        - {shipping_status} → session.case_context.shipping_status
        
        Args:
            raw_params: Params dict with possible placeholders
            session: Current session state
        
        Returns:
            Resolved params dict
        """
        # Build replacement map from session
        replacements = {
            "{order_id}": session.case_context.order_id,
            "{customer_id}": session.customer_info.customer_id,
            "{tracking_number}": session.case_context.tracking_number,
            "{item_name}": session.case_context.item_name,
            "{order_date}": session.case_context.order_date,
            "{shipping_status}": session.case_context.shipping_status,
            "{refund_reason}": session.case_context.refund_reason,
        }
        
        resolved = {}
        for key, value in raw_params.items():
            if isinstance(value, str) and value in replacements:
                # Replace placeholder
                resolved_value = replacements[value]
                if resolved_value is not None:
                    resolved[key] = resolved_value
                else:
                    # Keep original if no value in session
                    resolved[key] = value
            else:
                # Keep as-is (literal value)
                resolved[key] = value
        
        return resolved
    
    def to_trace_event(self, results: list) -> TraceEvent:
        """
        Convert action results to trace event.
        
        Args:
            results: List of ToolCallResult objects
        
        Returns:
            TraceEvent for session trace
        """
        return TraceEvent(
            agent="action",
            action="execute_tools",
            data={
                "tools_executed": [
                    {
                        "tool_name": r.tool_name,
                        "params": r.params,
                        "success": r.success,
                        "retry_count": r.retry_count,
                        "should_escalate": r.should_escalate
                    }
                    for r in results
                ],
                "total_calls": len(results),
                "success_count": sum(1 for r in results if r.success),
                "escalation_triggered": any(r.should_escalate for r in results)
            }
        )


# Global instance for easy import
action_agent = ActionAgent()
