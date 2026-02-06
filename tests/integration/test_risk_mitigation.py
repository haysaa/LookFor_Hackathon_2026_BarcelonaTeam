"""
Risk Mitigation Integration Tests
Tests for critical production risks identified.
"""
import pytest
from unittest.mock import Mock, patch
import os

from agents.triage_agent import TriageAgent
from agents.action_agent import ActionAgent
from tools.client import ToolsClient, ToolCallResult
from schemas.workflow import WorkflowDecision, ToolPlan
from schemas.session import Session, CustomerInfo, CaseContext
from config import get_fallback_message


class TestTriageConfidenceRisk:
    """Test Risk #1: Triage quality with low confidence."""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client."""
        with patch("agents.triage_agent.OpenAI") as mock_openai:
            client = Mock()
            mock_openai.return_value = client
            yield client
    
    def test_low_confidence_flags_needs_human(self, mock_openai_client):
        """Low confidence should automatically flag for human review."""
        # Set dummy API key to avoid validation error
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = TriageAgent(confidence_threshold=0.7)
            
            # Mock LLM response with low confidence
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '''
            {
                "intent": "WISMO",
                "confidence": 0.5,
                "entities": {"order_id": "123"},
                "needs_human": false,
                "reasoning": "Customer mentioned shipping"
            }
            '''
            mock_openai_client.chat.completions.create.return_value = mock_response
            
            result = agent.classify("paketim nerede acaba?")
            
            assert result.confidence == 0.5
            assert result.needs_human is True
            assert "[Low confidence:" in result.reasoning
    
    def test_high_confidence_no_flag(self, mock_openai_client):
        """High confidence should not flag for human."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            agent = TriageAgent(confidence_threshold=0.6)
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '''
            {
                "intent": "WISMO",
                "confidence": 0.92,
                "entities": {"order_id": "ORD-123"},
                "needs_human": false,
                "reasoning": "Clear WISMO request"
            }
            '''
            mock_openai_client.chat.completions.create.return_value = mock_response
            
            result = agent.classify("Where is my order #ORD-123?")
            
            assert result.confidence == 0.92
            assert result.needs_human is False
    
    def test_configurable_threshold(self):
        """Confidence threshold should be configurable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("agents.triage_agent.OpenAI"):
                strict_agent = TriageAgent(confidence_threshold=0.9)
                lenient_agent = TriageAgent(confidence_threshold=0.5)
                
                assert strict_agent.confidence_threshold == 0.9
                assert lenient_agent.confidence_threshold == 0.5


class TestLanguageConfigurationRisk:
    """Test Risk #2: Language/tone configuration."""
    
    def test_turkish_fallback_messages(self):
        """Turkish fallback messages should be available."""
        message = get_fallback_message("tool_failure", "tr")
        
        assert "Üzgünüz" in message or "sisteminizde" in message
        assert len(message) > 20
    
    def test_english_fallback_messages(self):
        """English fallback messages should be available."""
        message = get_fallback_message("tool_failure", "en")
        
        assert "sorry" in message.lower() or "issue" in message.lower()
        assert len(message) > 20
    
    def test_all_message_types_available(self):
        """All fallback message types should exist in both languages."""
        message_types = ["tool_failure", "low_confidence", "general_error", "escalated"]
        
        for msg_type in message_types:
            tr_msg = get_fallback_message(msg_type, "tr")
            en_msg = get_fallback_message(msg_type, "en")
            
            assert tr_msg, f"Missing TR message for {msg_type}"
            assert en_msg, f"Missing EN message for {msg_type}"
            assert tr_msg != en_msg, f"TR and EN messages are identical for {msg_type}"


class TestToolFailureHandlingRisk:
    """Test Risk #3: Tool failure UX and escalation."""
    
    @pytest.fixture
    def mock_tools_client(self):
        """Mock ToolsClient for testing."""
        return Mock(spec=ToolsClient)
    
    @pytest.fixture
    def action_agent(self, mock_tools_client):
        """Action agent with mock client."""
        return ActionAgent(tools_client=mock_tools_client)
    
    @pytest.fixture
    def sample_session(self):
        """Sample session."""
        return Session(
            session_id="test_123",
            customer_info=CustomerInfo(customer_id="cust_456"),
            case_context=CaseContext(order_id="ORD-789")
        )
    
    def test_single_tool_failure_provides_fallback(self, action_agent, mock_tools_client, sample_session):
        """Single tool failure should provide user-friendly fallback message."""
        decision = WorkflowDecision(
            workflow_id="TEST",
            next_action="call_tool",
            tool_plan=[ToolPlan(tool_name="test_tool", params={})]
        )
        
        # Mock tool failure
        mock_tools_client.execute.return_value = ToolCallResult(
            tool_name="test_tool",
            params={},
            success=False,
            data={},
            error="Network timeout",
            should_escalate=False
        )
        
        result = action_agent.execute(sample_session, decision)
        
        assert result["success"] is False
        assert result["fallback_message"] is not None
        assert len(result["fallback_message"]) > 20  # User-friendly message
        assert "Üzgünüz" in result["fallback_message"] or "sorry" in result["fallback_message"].lower()
    
    def test_multiple_failures_trigger_escalation(self, action_agent, mock_tools_client, sample_session):
        """Multiple tool failures should trigger escalation."""
        decision = WorkflowDecision(
            workflow_id="TEST",
            next_action="call_tool",
            tool_plan=[
                ToolPlan(tool_name="tool_1", params={}),
                ToolPlan(tool_name="tool_2", params={})
            ]
        )
        
        # Mock two failures
        mock_tools_client.execute.side_effect = [
            ToolCallResult(
                tool_name="tool_1",
                params={},
                success=False,
                data={},
                error="Error 1"
            ),
            ToolCallResult(
                tool_name="tool_2",
                params={},
                success=False,
                data={},
                error="Error 2"
            )
        ]
        
        # Patch config to ensure auto-escalation is enabled
        with patch("agents.action_agent.TOOL_FAILURE_THRESHOLD", 2):
            with patch("agents.action_agent.AUTO_ESCALATE_ON_TOOL_FAILURE", True):
                result = action_agent.execute(sample_session, decision)
        
        assert result["should_escalate"] is True
        assert result["fallback_message"] is not None
        # Should show escalation message
        assert "iletildi" in result["fallback_message"] or "forwarded" in result["fallback_message"].lower()
    
    def test_escalated_message_different_from_failure(self, action_agent, mock_tools_client, sample_session):
        """Escalation message should differ from tool failure message."""
        escalated_msg = get_fallback_message("escalated")
        tool_failure_msg = get_fallback_message("tool_failure")
        
        assert escalated_msg != tool_failure_msg
        assert len(escalated_msg) > 10
        assert len(tool_failure_msg) > 10


class TestConfigurationValidation:
    """Test configuration system validation."""
    
    def test_config_validates_on_import(self):
        """Config should validate values on import."""
        # This already passed if we got here, but let's be explicit
        from config import validate_config
        
        assert validate_config() is True
    
    def test_invalid_language_raises_error(self):
        """Invalid language should raise error."""
        from config import validate_config
        
        with patch.dict(os.environ, {"RESPONSE_LANGUAGE": "invalid"}):
            # Re-import would trigger validation
            # For now, just verify the validation function works
            with patch("config.RESPONSE_LANGUAGE", "invalid"):
                with pytest.raises(ValueError, match="Invalid RESPONSE_LANGUAGE"):
                    validate_config()
    
    def test_invalid_confidence_threshold_raises_error(self):
        """Invalid confidence threshold should raise error."""
        from config import validate_config
        
        with patch("config.TRIAGE_CONFIDENCE_THRESHOLD", 1.5):
            with pytest.raises(ValueError, match="TRIAGE_CONFIDENCE_THRESHOLD"):
                validate_config()


class TestEndToEndRiskScenarios:
    """Integration tests for complete risk scenarios."""
    
    def test_ambiguous_message_low_confidence_escalation(self):
        """Ambiguous message → low confidence → ask_clarifying/escalate."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("agents.triage_agent.OpenAI") as mock_openai_cls:
                client = Mock()
                mock_openai_cls.return_value = client
                
                agent = TriageAgent(confidence_threshold=0.7)
                
                # Ambiguous message gets low confidence
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = '''
                {
                    "intent": "UNKNOWN",
                    "confidence": 0.3,
                    "entities": {},
                    "needs_human": true,
                    "reasoning": "Message is ambiguous"
                }
                '''
                client.chat.completions.create.return_value = mock_response
                
                result = agent.classify("help me")
                
                # Should be flagged for human
                assert result.needs_human is True
                assert result.confidence < 0.7
                assert result.intent.value == "UNKNOWN"
    
    def test_tool_failure_after_retry_provides_clear_message(self):
        """Tool fails after retry → clear user message + escalation."""
        mock_client = Mock(spec=ToolsClient)
        action_agent = ActionAgent(tools_client=mock_client)
        
        session = Session(
            session_id="test_123",
            customer_info=CustomerInfo(customer_id="cust_456"),
            case_context=CaseContext(order_id="ORD-789")
        )
        
        decision = WorkflowDecision(
            workflow_id="WISMO",
            next_action="call_tool",
            tool_plan=[ToolPlan(tool_name="shopify_get_order_details", params={"order_id": "{order_id}"})]
        )
        
        # Tool fails with should_escalate
        mock_client.execute.return_value = ToolCallResult(
            tool_name="shopify_get_order_details",
            params={"order_id": "ORD-789"},
            success=False,
            data={},
            error="API unavailable after 2 retries",
            retry_count=2,
            should_escalate=True
        )
        
        result = action_agent.execute(session, decision)
        
        assert result["should_escalate"] is True
        assert result["fallback_message"] is not None
        assert len(result["fallback_message"]) > 30  # Substantial message
        # Should mention escalation or specialist team
        assert any(word in result["fallback_message"].lower() for word in ["uzman", "specialist", "ekip", "team"])
