"""
Agents Package - All agent implementations in one place.

Agents:
- TriageAgent: Classifies customer messages and extracts entities
- ActionAgent: Executes tools based on workflow decisions
- SupportAgent: Generates customer-facing responses
- EscalationAgent: Handles escalation to human support
"""
from app.agents.support import SupportAgent, support_agent
from app.agents.escalation import EscalationAgent, escalation_agent

# Triage and Action agents require API key, so we expose the classes
# rather than instances
from app.agents.triage import TriageAgent, triage_message, get_triage_agent
from app.agents.action import ActionAgent, action_agent

__all__ = [
    # Classes
    "TriageAgent",
    "ActionAgent", 
    "SupportAgent",
    "EscalationAgent",
    # Instances
    "support_agent",
    "escalation_agent",
    "action_agent",
    # Functions
    "triage_message",
    "get_triage_agent",
]
