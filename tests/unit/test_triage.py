"""
Unit Tests - Triage Agent
Version: 1.0
Developer: Dev B

Tests Triage Agent schema validation and mock classification.
NOTE: Full LLM tests require OPENAI_API_KEY environment variable.
"""
import pytest
import json
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from schemas.triage import TriageResult, Intent, ExtractedEntities, TRIAGE_RESULT_SCHEMA


class TestTriageSchema:
    """Test TriageResult schema validation."""
    
    def test_valid_wismo_result(self):
        """Test creating a valid WISMO triage result."""
        result = TriageResult(
            intent=Intent.WISMO,
            confidence=0.92,
            entities=ExtractedEntities(
                order_id="12345",
                tracking_number=None,
                item_name=None
            ),
            needs_human=False,
            reasoning="Customer asking about order status"
        )
        
        assert result.intent == Intent.WISMO
        assert result.confidence == 0.92
        assert result.entities.order_id == "12345"
        assert result.needs_human is False
    
    def test_valid_refund_result(self):
        """Test creating a valid REFUND_STANDARD triage result."""
        result = TriageResult(
            intent=Intent.REFUND_STANDARD,
            confidence=0.85,
            entities=ExtractedEntities(order_id="54321"),
            needs_human=False
        )
        
        assert result.intent == Intent.REFUND_STANDARD
        assert result.confidence == 0.85
    
    def test_valid_wrong_missing_result(self):
        """Test creating a valid WRONG_MISSING triage result."""
        result = TriageResult(
            intent=Intent.WRONG_MISSING,
            confidence=0.88,
            entities=ExtractedEntities(
                order_id="99999",
                item_name="Blue T-Shirt"
            ),
            needs_human=False
        )
        
        assert result.intent == Intent.WRONG_MISSING
        assert result.entities.item_name == "Blue T-Shirt"
    
    def test_low_confidence_needs_human(self):
        """Test that low confidence should flag needs_human."""
        result = TriageResult(
            intent=Intent.UNKNOWN,
            confidence=0.4,
            entities=ExtractedEntities(),
            needs_human=True,
            reasoning="Ambiguous message"
        )
        
        assert result.needs_human is True
        assert result.confidence < 0.6
    
    def test_confidence_bounds(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            TriageResult(
                intent=Intent.WISMO,
                confidence=1.5,  # Invalid
                entities=ExtractedEntities(),
                needs_human=False
            )
    
    def test_json_serialization(self):
        """Test JSON serialization of TriageResult."""
        result = TriageResult(
            intent=Intent.WISMO,
            confidence=0.9,
            entities=ExtractedEntities(order_id="123"),
            needs_human=False
        )
        
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        
        assert data["intent"] == "WISMO"
        assert data["confidence"] == 0.9
        assert data["entities"]["order_id"] == "123"


class TestTriageFixtures:
    """Test with triage fixtures from JSON file."""
    
    @pytest.fixture
    def fixtures(self):
        """Load triage test fixtures."""
        fixtures_path = Path(__file__).parent.parent / "fixtures" / "triage_fixtures.json"
        with open(fixtures_path) as f:
            return json.load(f)
    
    def test_fixtures_load(self, fixtures):
        """Test that fixtures load correctly."""
        assert "fixtures" in fixtures
        assert len(fixtures["fixtures"]) == 6
    
    def test_fixture_structure(self, fixtures):
        """Test fixture structure is valid."""
        for fixture in fixtures["fixtures"]:
            assert "id" in fixture
            assert "input" in fixture
            assert "expected" in fixture
            assert "message" in fixture["input"]
            assert "intent" in fixture["expected"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
