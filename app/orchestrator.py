"""
Orchestrator - Central coordination logic for multi-agent system.
Routes messages through agents: Triage → Workflow → (Action) → Support/Escalation
"""
from typing import Optional
from datetime import datetime
from app.models import (
    Session, SessionStatus, Message, MessageRole, Intent,
    EscalationPayload
)
from app.store import session_store
from app.trace import TraceLogger


class Orchestrator:
    """
    Central orchestrator that coordinates agent calls.
    
    Flow:
    1. Check session status (escalated = blocked)
    2. Log incoming message
    3. Call Triage Agent (if no intent yet or new topic)
    4. Call Workflow Engine (deterministic policy)
    5. Based on workflow decision:
       - ask_clarifying → generate clarifying question
       - call_tool → ActionAgent executes tools → re-run workflow
       - respond → SupportAgent generates response
       - escalate → EscalationAgent handles
    6. Return response to customer
    """
    
    def __init__(self):
        # Agent stubs - will be replaced with real implementations
        self.triage_agent = None  # Dev B
        self.workflow_engine = None  # Dev A
        self.action_agent = None  # Dev B
        self.support_agent = None  # Dev A
        self.escalation_agent = None  # Dev A
    
    def set_triage_agent(self, agent):
        """Inject Triage Agent (Dev B implementation)."""
        self.triage_agent = agent
    
    def set_workflow_engine(self, engine):
        """Inject Workflow Engine."""
        self.workflow_engine = engine
    
    def set_action_agent(self, agent):
        """Inject Action Agent (Dev B implementation)."""
        self.action_agent = agent
    
    def set_support_agent(self, agent):
        """Inject Support Agent."""
        self.support_agent = agent
    
    def set_escalation_agent(self, agent):
        """Inject Escalation Agent."""
        self.escalation_agent = agent
    
    def process_message(self, session_id: str, customer_message: str) -> dict:
        """
        Main entry point: process a customer message through the agent pipeline.
        
        Args:
            session_id: The session ID
            customer_message: Customer's message text
        
        Returns:
            dict with 'reply', 'status', 'intent', etc.
        """
        session = session_store.get(session_id)
        if not session:
            return {"error": "Session not found", "status": "error"}
        
        # Guard: escalated sessions are locked
        if session.status == SessionStatus.ESCALATED:
            return {
                "reply": "Your request has been escalated to our specialist team. We will get back to you shortly.",
                "status": SessionStatus.ESCALATED,
                "intent": session.intent,
                "locked": True
            }
        
        # Log incoming message
        message = Message(role=MessageRole.CUSTOMER, content=customer_message)
        session_store.add_message(session_id, message)
        TraceLogger.log_customer_message(session_id, customer_message)
        
        # Set contact day for WISMO workflow (only if not already set)
        session = session_store.get(session_id)
        if not session.case_context.contact_day:
            session.case_context.contact_day = datetime.utcnow().strftime("%a")
            session_store.update(session)
        
        # Step 1: Triage (if agent available)
        triage_result = self._run_triage(session_id, customer_message)
        
        # Step 2: Workflow decision
        workflow_decision = self._run_workflow(session_id)
        
        # Step 3: Execute based on decision
        response = self._execute_decision(session_id, workflow_decision)
        
        # Return final state
        session = session_store.get(session_id)
        return {
            "reply": response.get("reply", ""),
            "status": session.status,
            "intent": session.intent,
            "trace_event_count": len(session.trace)
        }
    
    def _run_triage(self, session_id: str, message: str) -> Optional[dict]:
        """Run triage agent to classify intent and extract entities."""
        if not self.triage_agent:
            # Stub: return unknown intent
            TraceLogger.log_triage_result(
                session_id,
                intent="UNKNOWN",
                confidence=0.0,
                entities={}
            )
            return {"intent": "UNKNOWN", "confidence": 0.0, "entities": {}}
        
        # Call actual triage agent - returns TriageResult Pydantic model
        triage_result = self.triage_agent.classify(message)
        
        # Convert Pydantic model to dict for compatibility
        result = {
            "intent": triage_result.intent.value if hasattr(triage_result.intent, 'value') else str(triage_result.intent),
            "confidence": triage_result.confidence,
            "entities": triage_result.entities.model_dump() if hasattr(triage_result.entities, 'model_dump') else {},
            "needs_human": triage_result.needs_human,
            "reasoning": triage_result.reasoning
        }
        
        # Update session with triage result
        session = session_store.get(session_id)
        if result.get("intent"):
            try:
                session.intent = Intent(result["intent"])
            except ValueError:
                session.intent = Intent.UNKNOWN
            session.confidence = result.get("confidence", 0.0)
        
        # Extract entities to case context
        entities = result.get("entities", {})
        if entities.get("order_id"):
            session.case_context.order_id = entities["order_id"]
        if entities.get("tracking_number"):
            session.case_context.tracking_number = entities["tracking_number"]
        if entities.get("item_name"):
            session.case_context.item_name = entities["item_name"]
        
        session_store.update(session)
        
        TraceLogger.log_triage_result(
            session_id,
            intent=result.get("intent", "UNKNOWN"),
            confidence=result.get("confidence", 0.0),
            entities=entities
        )
        
        return result
    
    def _run_workflow(self, session_id: str) -> dict:
        """Run workflow engine to get deterministic policy decision."""
        if not self.workflow_engine:
            # Stub: return respond action
            decision = {
                "workflow_id": "stub",
                "next_action": "respond",
                "policy_applied": ["stub_policy"],
                "required_fields_missing": [],
                "tool_plan": []
            }
            TraceLogger.log_workflow_decision(
                session_id,
                workflow_id=decision["workflow_id"],
                next_action=decision["next_action"],
                policy_applied=decision["policy_applied"]
            )
            return decision
        
        # Call actual workflow engine
        session = session_store.get(session_id)
        decision = self.workflow_engine.evaluate(session)
        
        TraceLogger.log_workflow_decision(
            session_id,
            workflow_id=decision.get("workflow_id", "unknown"),
            next_action=decision.get("next_action", "respond"),
            policy_applied=decision.get("policy_applied", []),
            required_fields_missing=decision.get("required_fields_missing", []),
            tool_plan=decision.get("tool_plan", [])
        )
        
        return decision
    
    def _execute_decision(self, session_id: str, decision: dict) -> dict:
        """Execute the workflow decision through appropriate agents."""
        next_action = decision.get("next_action", "respond")
        
        if next_action == "ask_clarifying":
            return self._handle_ask_clarifying(session_id, decision)
        
        elif next_action == "call_tool":
            return self._handle_tool_call(session_id, decision)
        
        elif next_action == "escalate":
            return self._handle_escalation(session_id, decision)
        
        elif next_action == "route_to_workflow":
            # Re-route to another workflow
            target = decision.get("target_workflow")
            session = session_store.get(session_id)
            if target:
                session.intent = Intent(target)
                session_store.update(session)
            return self._execute_decision(session_id, self._run_workflow(session_id))
        
        else:  # respond
            return self._handle_respond(session_id, decision)
    
    def _handle_ask_clarifying(self, session_id: str, decision: dict) -> dict:
        """Generate a clarifying question for missing fields."""
        missing = decision.get("required_fields_missing", [])
        
        # Map fields to questions (English only)
        field_questions = {
            "order_id": "Could you please provide your order number?",
            "item_photo": "Could you please share a photo of the items you received?",
            "packing_slip": "Could you please share a photo of the packing slip?",
            "shipping_label": "Could you please share a photo of the shipping label?",
            "refund_reason": "Could you please let us know the reason for your refund request?"
        }
        
        questions = [field_questions.get(f, f"Please provide your {f}.") for f in missing]
        reply = " ".join(questions) if questions else "Could you please provide more details?"
        
        # Save response
        response_msg = Message(role=MessageRole.AGENT, content=reply)
        session_store.add_message(session_id, response_msg)
        TraceLogger.log_agent_response(session_id, "support", reply)
        
        return {"reply": reply}
    
    def _handle_tool_call(self, session_id: str, decision: dict) -> dict:
        """Execute tools via ToolsClient directly."""
        from app.tools.client import tools_client
        
        session = session_store.get(session_id)
        tool_plan = decision.get("tool_plan", [])
        
        if not tool_plan:
            # No tools to execute, just respond
            return self._handle_respond(session_id, decision)
        
        # Execute each tool
        all_success = True
        should_escalate = False
        last_result = None  # Store last successful tool result for response generation
        
        for tool_item in tool_plan:
            tool_name = tool_item.get("tool_name") if isinstance(tool_item, dict) else getattr(tool_item, "tool_name", None)
            params = tool_item.get("params", {}) if isinstance(tool_item, dict) else getattr(tool_item, "params", {})
            
            if not tool_name:
                continue
            
            # Resolve placeholders from session context
            resolved_params = {}
            for key, value in params.items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    field = value[1:-1]  # Remove braces
                    if hasattr(session.case_context, field):
                        resolved_params[key] = getattr(session.case_context, field)
                    else:
                        resolved_params[key] = value
                else:
                    resolved_params[key] = value
            
            # Execute tool
            result = tools_client.execute(
                session_id=session_id,
                tool_name=tool_name,
                params=resolved_params
            )
            
            # Store the last successful result for response generation
            last_result = result
            
            if not result.get("success"):
                all_success = False
            
            if result.get("should_escalate"):
                should_escalate = True
                break
            
            # Update session context with tool results
            if result.get("success") and result.get("data"):
                data = result["data"]
                if data.get("status"):
                    session.case_context.shipping_status = data["status"]
                if data.get("tracking_number"):
                    session.case_context.tracking_number = data["tracking_number"]
                session_store.update(session)
        
        # Check for escalation
        if should_escalate:
            return self._handle_escalation(session_id, {
                "escalation_reason": "Tool execution failed after retry"
            })
        
        # Tool executed successfully - generate response based on tool results
        # Don't re-run workflow to avoid recursion
        return self._handle_respond(session_id, decision, last_result)
    
    def _handle_escalation(self, session_id: str, decision: dict) -> dict:
        """Handle escalation - lock session and generate messages."""
        session = session_store.get(session_id)
        reason = decision.get("escalation_reason", "Requires human review")
        
        # Create escalation payload
        payload = EscalationPayload(
            customer_id=session.customer_info.shopify_customer_id,
            reason=reason,
            conversation_summary=self._summarize_conversation(session),
            attempted_actions=[t.tool_name for t in session.tool_history],
            priority=self._calculate_priority(session)
        )
        
        # Lock session
        session_store.set_status(session_id, SessionStatus.ESCALATED)
        
        # Log escalation
        TraceLogger.log_escalation(session_id, reason, payload.model_dump())
        
        # Customer message
        reply = "Your request has been escalated to our specialist team. We will get back to you within 24 hours. Thank you for your patience."
        
        response_msg = Message(role=MessageRole.AGENT, content=reply)
        session_store.add_message(session_id, response_msg)
        TraceLogger.log_agent_response(session_id, "escalation", reply)
        
        return {
            "reply": reply,
            "escalation_payload": payload.model_dump()
        }
    
    def _handle_respond(self, session_id: str, decision: dict, tool_results: dict = None) -> dict:
        """Generate response via Support Agent."""
        if not self.support_agent:
            # Stub response - include tool data if available
            if tool_results and tool_results.get("success") and tool_results.get("data"):
                data = tool_results["data"]
                template = f"Your order status is: {data.get('status', 'N/A')}. "
                if data.get("estimated_delivery"):
                    template += f"Estimated delivery: {data['estimated_delivery']}. "
                if data.get("tracking_number"):
                    template += f"Tracking: {data['tracking_number']}."
            else:
                template = decision.get("response_template", "We're happy to assist you.")
            
            response_msg = Message(role=MessageRole.AGENT, content=template)
            session_store.add_message(session_id, response_msg)
            TraceLogger.log_agent_response(session_id, "support", template)
            
            return {"reply": template}
        
        # Generate response via Support Agent
        session = session_store.get(session_id)
        response = self.support_agent.generate_response(session, decision, tool_results)
        
        response_msg = Message(role=MessageRole.AGENT, content=response["body"])
        session_store.add_message(session_id, response_msg)
        TraceLogger.log_agent_response(
            session_id, "support",
            response["body"],
            subject=response.get("subject")
        )
        
        return {"reply": response["body"]}
    
    def _summarize_conversation(self, session: Session) -> str:
        """Create a brief summary of the conversation for escalation."""
        messages = session.messages[-5:]  # Last 5 messages
        summary_parts = []
        for msg in messages:
            role = "Müşteri" if msg.role == MessageRole.CUSTOMER else "Bot"
            summary_parts.append(f"{role}: {msg.content[:100]}...")
        return "\n".join(summary_parts)
    
    def _calculate_priority(self, session: Session) -> str:
        """Calculate escalation priority based on context."""
        # High priority: multiple tool failures or VIP customer
        if len([t for t in session.tool_history if not t.success]) >= 2:
            return "high"
        # Medium priority: default
        return "medium"


# Global orchestrator instance with agents wired in
orchestrator = Orchestrator()
# Workflow engine will be wired when available

# Import and wire other agents (lazy import to avoid circular deps)
def wire_agents():
    """Wire all available agents into the orchestrator."""
    from app.agents.support import support_agent
    from app.agents.escalation import escalation_agent
    from app.workflow_engine import workflow_engine
    
    orchestrator.set_support_agent(support_agent)
    orchestrator.set_escalation_agent(escalation_agent)
    orchestrator.set_workflow_engine(workflow_engine)
    
    # Wire Triage Agent (requires API key)
    try:
        from app.agents.triage import TriageAgent
        triage_agent = TriageAgent()
        orchestrator.set_triage_agent(triage_agent)
    except Exception as e:
        print(f"Warning: Could not initialize TriageAgent: {e}")
    
    # Wire Action Agent
    try:
        from app.agents.action import ActionAgent
        action_agent = ActionAgent()
        orchestrator.set_action_agent(action_agent)
    except Exception as e:
        print(f"Warning: Could not initialize ActionAgent: {e}")

wire_agents()


