"""
Triage Agent
Version: 1.0
Developer: Dev B (moved to app/agents by Dev A)

Classifies customer messages into intents and extracts entities.
Uses OpenAI GPT-4o mini with structured JSON outputs.
"""
import os
import json
from typing import Optional
from openai import OpenAI
from pathlib import Path

from schemas.triage import TriageResult, Intent, ExtractedEntities, TRIAGE_RESULT_SCHEMA
from utils.prompt_renderer import PromptRenderer
from config import TRIAGE_CONFIDENCE_THRESHOLD, TRIAGE_LOW_CONFIDENCE_ACTION, get_fallback_message


class TriageAgent:
    """
    Triage Agent for intent classification and entity extraction.
    
    Uses OpenAI GPT-4o mini with structured outputs to ensure
    consistent JSON response format.
    
    Intents:
        - WISMO: Where Is My Order (shipping delays, tracking, delivery)
        - REFUND_STANDARD: Refund requests
        - WRONG_MISSING: Wrong or missing items in parcel
        - UNKNOWN: Cannot determine intent
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        prompt_version: str = "v1",
        confidence_threshold: Optional[float] = None
    ):
        """
        Initialize Triage Agent.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
            prompt_version: Prompt template version
            confidence_threshold: Minimum confidence to accept classification (defaults to config)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.prompt_version = prompt_version
        self.confidence_threshold = confidence_threshold or TRIAGE_CONFIDENCE_THRESHOLD
        self.renderer = PromptRenderer()
        self.template_name = f"triage_agent_{prompt_version}"
    
    def classify(
        self,
        customer_message: str,
        customer_context: Optional[str] = None
    ) -> TriageResult:
        """
        Classify customer message and extract entities.
        
        Args:
            customer_message: The customer's message text
            customer_context: Optional context about the customer (VIP, history, etc.)
        
        Returns:
            TriageResult with intent, confidence, entities, and needs_human flag
        """
        # Render prompt with variables
        prompt = self.renderer.render(self.template_name, {
            "customer_message": customer_message,
            "customer_context": customer_context or "No additional context"
        })
        
        try:
            # Call OpenAI with structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a customer service triage agent. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=500
            )
            
            # Parse response
            content = response.choices[0].message.content
            if not content:
                return self._create_unknown_result("Empty response from LLM")
            
            result_dict = json.loads(content)
            
            # Validate and create TriageResult
            result = self._parse_result(result_dict)
            
            # RISK MITIGATION: Auto-flag for human if confidence is low
            if result.confidence < self.confidence_threshold:
                result.needs_human = True
                # Add warning to reasoning
                warning = f" [Low confidence: {result.confidence:.2f} < {self.confidence_threshold}]"
                result.reasoning = (result.reasoning or "") + warning
            
            return result
            
        except json.JSONDecodeError as e:
            return self._create_unknown_result(f"JSON parse error: {e}")
        except Exception as e:
            return self._create_unknown_result(f"API error: {e}")
    
    def _parse_result(self, data: dict) -> TriageResult:
        """Parse LLM response into TriageResult."""
        try:
            # Handle intent
            intent_str = data.get("intent", "UNKNOWN").upper()
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.UNKNOWN
            
            # Handle entities
            entities_data = data.get("entities", {})
            entities = ExtractedEntities(
                order_id=entities_data.get("order_id"),
                tracking_number=entities_data.get("tracking_number"),
                item_name=entities_data.get("item_name")
            )
            
            return TriageResult(
                intent=intent,
                confidence=float(data.get("confidence", 0.5)),
                entities=entities,
                needs_human=data.get("needs_human", False),
                reasoning=data.get("reasoning")
            )
        except Exception:
            return self._create_unknown_result("Failed to parse response")
    
    def _create_unknown_result(self, reason: str) -> TriageResult:
        """Create an UNKNOWN result with needs_human=True."""
        return TriageResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            entities=ExtractedEntities(),
            needs_human=True,
            reasoning=reason
        )
    
    def to_trace_event(self, result: TriageResult) -> dict:
        """
        Convert result to trace event format.
        
        Returns:
            Dict suitable for adding to session trace
        """
        return {
            "agent": "triage",
            "action": "classify",
            "data": {
                "intent": result.intent.value,
                "confidence": result.confidence,
                "entities": result.entities.model_dump(),
                "needs_human": result.needs_human
            }
        }


# Global instance (created lazily to avoid import errors when API key not set)
_triage_agent = None

def get_triage_agent() -> TriageAgent:
    """Get or create the global triage agent instance."""
    global _triage_agent
    if _triage_agent is None:
        _triage_agent = TriageAgent()
    return _triage_agent


# Convenience function for quick classification
def triage_message(
    message: str,
    context: Optional[str] = None,
    api_key: Optional[str] = None
) -> TriageResult:
    """
    Quick function to classify a message without instantiating agent.
    
    Args:
        message: Customer message
        context: Optional customer context
        api_key: OpenAI API key
    
    Returns:
        TriageResult
    """
    agent = TriageAgent(api_key=api_key)
    return agent.classify(message, context)
