"""
Real Ticket Store Tests
=======================
Tests for TicketStore with real anonymized ticket format support.
"""
import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tickets import (
    TicketStore,
    TicketRecord,
    parse_real_ticket,
    parse_dummy_ticket,
    parse_conversation_to_turns,
    parse_date,
    tokenize,
    detect_ticket_format,
)


# ============================================================================
# Sample Data (mirrors real schema for CI testing)
# ============================================================================

SAMPLE_REAL_TICKET = {
    "conversationId": "conv_test_001",
    "customerId": "cust_abc123",
    "createdAt": "19-Jul-2025 14:58:48",
    "conversationType": "email",
    "subject": "Cancel my subscription please",
    "conversation": (
        "Customer's message: Hi, I want to cancel my subscription. "
        "I've been charged twice this month. "
        "Agent's message: I'm sorry to hear that. Let me check your account. "
        "Customer's message: Please hurry, I need this resolved today. "
        "Agent's message: I've processed the cancellation and refund."
    )
}

SAMPLE_DUMMY_TICKET = {
    "conversationId": "wismo-test@email.com",
    "customerId": "cust_dummy_001",
    "createdAt": "03-Feb-2026 10:30:00",
    "ConversationType": "email",
    "subject": "Where is my order?",
    "conversation": "Hello, I ordered 3 days ago but there is still no shipping info."
}

SAMPLE_REAL_TICKETS_ARRAY = [
    SAMPLE_REAL_TICKET,
    {
        "conversationId": "conv_test_002",
        "customerId": "cust_xyz789",
        "createdAt": "20-Jul-2025 09:30:00",
        "conversationType": "email",
        "subject": "Discount code not working",
        "conversation": (
            "Customer's message: The discount code SAVE20 is not working. "
            "Agent's message: Let me check that for you. "
            "Customer's message: I tried multiple times already."
        )
    }
]


# ============================================================================
# Test: Parsing Functions
# ============================================================================

class TestParsing:
    """Tests for parsing functions."""
    
    def test_parse_date_standard_format(self):
        """Parse date in DD-Mon-YYYY HH:MM:SS format."""
        dt = parse_date("19-Jul-2025 14:58:48")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 7
        assert dt.day == 19
        assert dt.hour == 14
    
    def test_parse_date_returns_none_on_invalid(self):
        """Returns None for invalid date strings."""
        assert parse_date("") is None
        assert parse_date("invalid") is None
        assert parse_date(None) is None
    
    def test_parse_conversation_to_turns_with_markers(self):
        """Parse conversation with Customer's/Agent's message markers."""
        text = (
            "Customer's message: Hello, I need help. "
            "Agent's message: How can I assist you?"
        )
        turns = parse_conversation_to_turns(text)
        
        assert len(turns) == 2
        assert turns[0]["role"] == "customer"
        assert "Hello" in turns[0]["text"]
        assert turns[1]["role"] == "agent"
        assert "assist" in turns[1]["text"]
    
    def test_parse_conversation_to_turns_no_markers(self):
        """Plain text without markers -> single customer turn."""
        text = "I need to track my order please."
        turns = parse_conversation_to_turns(text)
        
        assert len(turns) == 1
        assert turns[0]["role"] == "customer"
        assert "track" in turns[0]["text"]
    
    def test_parse_conversation_to_turns_multiple_turns(self):
        """Multiple alternating turns."""
        turns = parse_conversation_to_turns(SAMPLE_REAL_TICKET["conversation"])
        
        assert len(turns) >= 4
        # Verify alternating pattern
        roles = [t["role"] for t in turns]
        assert roles[0] == "customer"
        assert roles[1] == "agent"
    
    def test_tokenize_basic(self):
        """Tokenize text into keywords."""
        tokens = tokenize("Hello, I need help with my ORDER!")
        
        assert "hello" in tokens
        assert "need" in tokens
        assert "help" in tokens
        assert "order" in tokens
        # Short tokens filtered
        assert "my" not in tokens
        assert "i" not in tokens
    
    def test_tokenize_empty(self):
        """Empty text returns empty set."""
        assert tokenize("") == set()
        assert tokenize(None) == set()


# ============================================================================
# Test: Real Ticket Parsing
# ============================================================================

class TestRealTicketParsing:
    """Tests for real ticket format parsing."""
    
    def test_parse_real_ticket_basic(self):
        """Parse real ticket with all fields."""
        record = parse_real_ticket(SAMPLE_REAL_TICKET)
        
        assert record.id == "conv_test_001"
        assert record.customer_id == "cust_abc123"
        assert record.channel == "email"
        assert record.subject == "Cancel my subscription please"
        assert record.created_at is not None
        assert record.created_at.year == 2025
    
    def test_parse_real_ticket_has_turns(self):
        """Real ticket has parsed turns."""
        record = parse_real_ticket(SAMPLE_REAL_TICKET)
        
        assert len(record.turns) >= 2
        customer_turns = [t for t in record.turns if t["role"] == "customer"]
        assert len(customer_turns) >= 1
    
    def test_parse_real_ticket_has_tokens(self):
        """Real ticket has keyword tokens."""
        record = parse_real_ticket(SAMPLE_REAL_TICKET)
        
        assert len(record.tokens) > 0
        # Should include words from subject and customer messages
        assert "cancel" in record.tokens
        assert "subscription" in record.tokens
    
    def test_detect_format_real(self):
        """Detect real format from markers."""
        fmt = detect_ticket_format(SAMPLE_REAL_TICKETS_ARRAY)
        assert fmt == "real"
    
    def test_detect_format_dummy(self):
        """Detect dummy format (no markers)."""
        fmt = detect_ticket_format([SAMPLE_DUMMY_TICKET])
        assert fmt == "dummy"


# ============================================================================
# Test: Dummy Ticket Parsing
# ============================================================================

class TestDummyTicketParsing:
    """Tests for dummy ticket format parsing."""
    
    def test_parse_dummy_ticket_basic(self):
        """Parse dummy ticket with all fields."""
        record = parse_dummy_ticket(SAMPLE_DUMMY_TICKET)
        
        assert record.id == "wismo-test@email.com"
        assert record.customer_id == "cust_dummy_001"
        assert record.subject == "Where is my order?"
    
    def test_parse_dummy_ticket_has_tokens(self):
        """Dummy ticket has keyword tokens."""
        record = parse_dummy_ticket(SAMPLE_DUMMY_TICKET)
        
        assert "order" in record.tokens
        assert "shipping" in record.tokens


# ============================================================================
# Test: TicketStore
# ============================================================================

class TestTicketStore:
    """Tests for TicketStore functionality."""
    
    def test_load_and_search(self):
        """Load tickets and search."""
        store = TicketStore()
        
        # Manually ingest sample data
        for obj in SAMPLE_REAL_TICKETS_ARRAY:
            record = parse_real_ticket(obj)
            store._records[record.id] = record
        
        # Search for subscription
        results = store.search_similar("cancel subscription", limit=3)
        
        assert len(results) >= 1
        # First result should be about subscription
        assert "subscription" in results[0].tokens or "cancel" in results[0].tokens
    
    def test_search_similar_returns_relevant(self):
        """Search returns relevant tickets."""
        store = TicketStore()
        
        # Ingest both samples
        for obj in SAMPLE_REAL_TICKETS_ARRAY:
            record = parse_real_ticket(obj)
            store._records[record.id] = record
        
        # Search for discount code
        results = store.search_similar("discount code not working", limit=3)
        
        assert len(results) >= 1
        # Should find discount-related ticket
        found_discount = any("discount" in r.tokens for r in results)
        assert found_discount, "Should find ticket with 'discount' in tokens"
    
    def test_dedup_by_conversation_id(self):
        """Duplicate conversationIds are deduped."""
        store = TicketStore()
        
        # Same ticket twice
        record1 = parse_real_ticket(SAMPLE_REAL_TICKET)
        record2 = parse_real_ticket(SAMPLE_REAL_TICKET)
        
        store._records[record1.id] = record1
        store._records[record2.id] = record2  # Same ID, overwrites
        
        assert store.count() == 1
    
    def test_get_by_customer_id(self):
        """Get tickets by customer ID."""
        store = TicketStore()
        
        record = parse_real_ticket(SAMPLE_REAL_TICKET)
        store._records[record.id] = record
        store._by_customer[record.customer_id] = [record.id]
        
        results = store.get_by_customer_id("cust_abc123")
        assert len(results) == 1
        assert results[0].id == "conv_test_001"


# ============================================================================
# Test: Fallback Behavior
# ============================================================================

class TestFallback:
    """Tests for fallback to dummy fixtures."""
    
    def test_loader_handles_missing_file(self):
        """load_from_json handles missing file gracefully."""
        store = TicketStore()
        count = store.load_from_json("/nonexistent/path/to/tickets.json")
        
        assert count == 0
        assert store.count() == 0
    
    def test_loader_handles_invalid_json(self, tmp_path):
        """load_from_json handles invalid JSON gracefully."""
        # Create invalid JSON file
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")
        
        store = TicketStore()
        count = store.load_from_json(str(bad_file))
        
        assert count == 0
    
    def test_dummy_fixtures_exist(self):
        """Dummy fixtures file exists in expected location."""
        fixtures_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'fixtures',
            'tickets_dummy.json'
        )
        assert os.path.exists(fixtures_path), "Dummy fixtures should exist"


# ============================================================================
# Test: Integration with Real File (Optional)
# ============================================================================

class TestRealFileIntegration:
    """
    Integration tests with real ticket file.
    Skipped if file not available locally.
    """
    
    @pytest.fixture
    def real_tickets_path(self):
        """Path to real tickets file."""
        # Check common locations
        paths = [
            os.getenv("TICKETS_PATH"),
            "fixtures/tickets_real.json",
            "/mnt/data/anonymized_tickets (1).json",
        ]
        for path in paths:
            if path and os.path.exists(path):
                return path
        return None
    
    def test_load_real_tickets_parses_and_indexes(self, real_tickets_path):
        """Load real tickets file and verify parsing."""
        if not real_tickets_path:
            pytest.skip("Real tickets file not available")
        
        store = TicketStore()
        count = store.load_from_json(real_tickets_path)
        
        assert count > 0, "Should load at least one ticket"
        
        # Check first ticket
        records = store.get_all_records()
        first = records[0]
        
        assert first.id, "Should have ID"
        assert len(first.turns) >= 1, "Should have at least one turn"
        assert len(first.tokens) > 0, "Should have tokens"
