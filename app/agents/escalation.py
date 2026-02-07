"""
Escalation Agent - Handles escalation to human agents.
Creates structured escalation payloads and locks sessions.
"""
from datetime import datetime
import uuid
from typing import Optional
from app.models import Session, EscalationPayload, SessionStatus, MessageRole
from app.store import session_store
from app.trace import TraceLogger


class EscalationAgent:
    """
    Handles escalation of customer issues to human agents.
    
    Triggers:
    - Policy outside automation scope
    - Tool failure after retry
    - Low confidence triage (< 0.6)
    - Customer explicit request for human
    """
    
    # Standard customer message for escalation
    CUSTOMER_MESSAGE = "Your request has been escalated to our specialist team. We will get back to you within 24 hours. Thank you for your patience."
    
    def escalate(
        self,
        session_id: str,
        reason: str,
        priority: Optional[str] = None
    ) -> dict:
        """
        Escalate a session to human agents.
        
        Args:
            session_id: Session to escalate
            reason: Reason for escalation
            priority: Optional priority override (low/medium/high)
        
        Returns:
            dict with escalation_payload and customer_message
        """
        session = session_store.get(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Calculate priority if not provided
        if not priority:
            priority = self._calculate_priority(session, reason)
        
        # Create escalation payload (matching required schema)
        payload = EscalationPayload(
            escalation_id=f"esc_{uuid.uuid4().hex[:8]}",
            customer_id=session.customer_info.shopify_customer_id,
            reason=reason,
            conversation_summary=self._summarize_conversation(session),
            attempted_actions=self._get_attempted_actions(session),
            priority=priority,
            created_at=datetime.utcnow().isoformat()
        )
        
        # Lock the session
        session_store.set_status(session_id, SessionStatus.ESCALATED)
        
        # Log to trace
        TraceLogger.log_escalation(
            session_id=session_id,
            reason=reason,
            payload=payload.model_dump()
        )
        
        return {
            "escalation_payload": payload.model_dump(),
            "customer_message": self.CUSTOMER_MESSAGE,
            "session_locked": True
        }
    
    def should_escalate(self, session: Session, decision: Optional[dict] = None) -> tuple[bool, str]:
        """
        Check if a session should be escalated.
        
        Returns:
            tuple of (should_escalate: bool, reason: str)
        """
        # Check triage confidence
        if session.confidence > 0 and session.confidence < 0.6:
            return True, "Low confidence triage result"
        
        # Check for tool failures
        failed_tools = [t for t in session.tool_history if not t.success]
        if len(failed_tools) >= 2:
            return True, "Multiple tool failures"
        
        # Check workflow decision
        if decision and decision.get("next_action") == "escalate":
            return True, decision.get("escalation_reason", "Workflow requires escalation")
        
        # Check for tool that requires escalation
        if decision and decision.get("should_escalate"):
            return True, "Tool execution requires human approval"
        
        return False, ""
    
    def _calculate_priority(self, session: Session, reason: str) -> str:
        """Calculate escalation priority based on context."""
        # High priority triggers
        high_priority_keywords = ["urgent", "acil", "hemen", "fraud", "dolandırıcılık"]
        
        # Check messages for urgency
        for msg in session.messages:
            if msg.role == MessageRole.CUSTOMER:
                if any(kw in msg.content.lower() for kw in high_priority_keywords):
                    return "high"
        
        # Multiple tool failures = high priority
        failed = [t for t in session.tool_history if not t.success]
        if len(failed) >= 2:
            return "high"
        
        # VIP check would go here (based on customer tier)
        
        return "medium"
    
    def _summarize_conversation(self, session: Session) -> str:
        """Create a brief summary for human agents."""
        summary_parts = []
        
        # Intent
        if session.intent:
            summary_parts.append(f"Konu: {session.intent.value}")
        
        # Last few messages
        recent_messages = session.messages[-5:]
        for msg in recent_messages:
            role = "Müşteri" if msg.role == MessageRole.CUSTOMER else "Bot"
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            summary_parts.append(f"{role}: {content}")
        
        return "\n".join(summary_parts)
    
    def _get_attempted_actions(self, session: Session) -> list[str]:
        """Get list of attempted actions for escalation context."""
        actions = []
        
        # Add tool calls
        for tool in session.tool_history:
            status = "✓" if tool.success else "✗"
            actions.append(f"{tool.tool_name} [{status}]")
        
        # Add workflow decisions from trace
        for event in session.trace:
            if event.event_type.value == "workflow_decision":
                action = event.data.get("next_action", "unknown")
                policy = event.data.get("policy_applied", [])
                if policy:
                    actions.append(f"Policy: {', '.join(policy)}")
        
        return actions


# Global instance
escalation_agent = EscalationAgent()
