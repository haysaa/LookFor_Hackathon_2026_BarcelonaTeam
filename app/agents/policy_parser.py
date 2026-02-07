"""
Policy Parser Agent - Converts natural language prompts to structured overrides

Uses OpenAI to parse prompts like:
"If a customer wants to update their order address, do not update it directly. 
 Mark the order as 'NEEDS_ATTENTION' and escalate the situation."

Into structured format:
{
  "workflow": "ORDER_MODIFICATION",
  "rule_pattern": "address_change",
  "action_override": "escalate",
  "context_updates": {"NEEDS_ATTENTION": true}
}
"""

import os
from typing import Dict, Optional
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


AVAILABLE_WORKFLOWS = [
    "WISMO",
    "REFUND_STANDARD",
    "WRONG_MISSING",
    "ORDER_MODIFICATION",
    "POSITIVE_FEEDBACK",
    "SUBSCRIPTION_BILLING",
    "DISCOUNT_PROMO"
]

AVAILABLE_ACTIONS = [
    "call_tool",
    "respond",
    "ask_clarifying",
    "escalate",
    "route_to_workflow"
]

SYSTEM_PROMPT = f"""You are a policy override parser for a multi-agent customer support system.

Your job is to parse natural language policy updates into structured JSON that modifies workflow behavior.

Available Workflows:
{', '.join(AVAILABLE_WORKFLOWS)}

Available Actions:
- call_tool: Execute a tool (e.g., update address, create credit)
- respond: Send a message to customer
- ask_clarifying: Request more information
- escalate: Send to human team
- route_to_workflow: Redirect to another workflow

Common Patterns:
- "update address" → ORDER_MODIFICATION workflow, address_change rule
- "cancel subscription" → SUBSCRIPTION_BILLING workflow, cancel rule
- "expired promo code" → DISCOUNT_PROMO workflow, expired rule
- "wrong item" → WRONG_MISSING workflow

Extract from the prompt:
1. Which workflow is affected?
2. Which rule/scenario (pattern match)?
3. What should the NEW action be?
4. Any context to set (e.g., NEEDS_ATTENTION: true)?
5. If escalating, what's the reason?

Be intelligent about matching. "Address update" could be "address_change", "update_address", etc.
"""


def parse_policy_prompt(prompt: str) -> Dict:
    """
    Parse natural language policy prompt into structured override.
    
    Args:
        prompt: Natural language policy update
        
    Returns:
        Dict with: workflow, rule_pattern, action_override, context_updates, etc.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse this policy update:\n\n{prompt}"}
        ],
        functions=[
            {
                "name": "create_policy_override",
                "description": "Create a structured policy override from natural language",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_workflow": {
                            "type": "string",
                            "enum": AVAILABLE_WORKFLOWS,
                            "description": "Which workflow to modify"
                        },
                        "rule_pattern": {
                            "type": "string",
                            "description": "Pattern to match rule (e.g., 'address_change', 'cancel', 'expired')"
                        },
                        "action_override": {
                            "type": "string",
                            "enum": AVAILABLE_ACTIONS,
                            "description": "New action to take"
                        },
                        "context_updates": {
                            "type": "object",
                            "description": "Context variables to set (e.g., {\"NEEDS_ATTENTION\": true})",
                            "additionalProperties": True
                        },
                        "escalation_reason": {
                            "type": "string",
                            "description": "Reason for escalation (if action is escalate)"
                        },
                        "tool_param_overrides": {
                            "type": "object",
                            "description": "Override tool parameters (e.g., {\"value\": 0.20} for discount)",
                            "additionalProperties": True
                        },
                        "response_template_override": {
                            "type": "string",
                            "description": "Custom response message"
                        }
                    },
                    "required": ["target_workflow", "rule_pattern", "action_override"]
                }
            }
        ],
        function_call={"name": "create_policy_override"}
    )
    
    # Extract function call result
    import json
    function_args = response.choices[0].message.function_call.arguments
    parsed = json.loads(function_args)
    
    return parsed


class PolicyParserAgent:
    """Agent that parses policy prompts into structured overrides"""
    
    def __init__(self):
        self.client = client
    
    def parse(self, prompt: str) -> Dict:
        """Parse policy prompt"""
        return parse_policy_prompt(prompt)
    
    def validate_override(self, override_data: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate parsed override data.
        
        Returns: (is_valid, error_message)
        """
        required = ["target_workflow", "rule_pattern", "action_override"]
        
        for field in required:
            if field not in override_data:
                return False, f"Missing required field: {field}"
        
        if override_data["target_workflow"] not in AVAILABLE_WORKFLOWS:
            return False, f"Invalid workflow: {override_data['target_workflow']}"
        
        
        if override_data["action_override"] not in AVAILABLE_ACTIONS:
            return False, f"Invalid action: {override_data['action_override']}"
        
        # If action is escalate, escalation_reason should be provided
        if override_data["action_override"] == "escalate":
            if not override_data.get("escalation_reason"):
                # Auto-generate if missing
                override_data["escalation_reason"] = f"Policy override - {override_data['rule_pattern']} requires manual review"
        
        return True, None
