"""
Unit tests for TicketStore.
"""
import pytest
from app.tickets import TicketStore, Ticket, ticket_store, load_dummy_fixtures


class TestTicketStore:
    """Unit tests for TicketStore."""
    
    def setup_method(self):
        """Fresh store for each test."""
        ticket_store.clear()
    
    def test_ingest_tickets(self):
        """Ingest tickets from list."""
        tickets = [
            {
                "conversationId": "test-001@email.com",
                "customerId": "cust_test1",
                "createdAt": "06-Feb-2026 10:00:00",
                "ConversationType": "email",
                "subject": "Test subject",
                "conversation": "Test conversation"
            }
        ]
        
        count = ticket_store.ingest(tickets)
        
        assert count == 1
        assert ticket_store.count() == 1
    
    def test_get_by_conversation_id(self):
        """Retrieve ticket by conversation ID."""
        tickets = [
            {
                "conversationId": "conv-123@email.com",
                "customerId": "cust_abc",
                "createdAt": "06-Feb-2026 10:00:00",
                "subject": "Test",
                "conversation": "Content"
            }
        ]
        ticket_store.ingest(tickets)
        
        result = ticket_store.get_by_conversation_id("conv-123@email.com")
        
        assert result is not None
        assert result.customer_id == "cust_abc"
    
    def test_get_by_customer_id(self):
        """Retrieve all tickets for a customer."""
        tickets = [
            {"conversationId": "c1", "customerId": "cust_same", "createdAt": "01-Feb-2026 10:00:00", "subject": "S1", "conversation": "C1"},
            {"conversationId": "c2", "customerId": "cust_same", "createdAt": "02-Feb-2026 10:00:00", "subject": "S2", "conversation": "C2"},
            {"conversationId": "c3", "customerId": "cust_other", "createdAt": "03-Feb-2026 10:00:00", "subject": "S3", "conversation": "C3"},
        ]
        ticket_store.ingest(tickets)
        
        results = ticket_store.get_by_customer_id("cust_same")
        
        assert len(results) == 2
    
    def test_search_similar(self):
        """Search for similar tickets by keyword."""
        tickets = [
            {"conversationId": "c1", "customerId": "cust_1", "createdAt": "01-Feb-2026 10:00:00", "subject": "Sipariş nerede", "conversation": "kargo bekliyorum"},
            {"conversationId": "c2", "customerId": "cust_2", "createdAt": "02-Feb-2026 10:00:00", "subject": "İade talebi", "conversation": "refund istiyorum"},
            {"conversationId": "c3", "customerId": "cust_3", "createdAt": "03-Feb-2026 10:00:00", "subject": "Kargo gecikmesi", "conversation": "sipariş gecikti kargo yok"},
        ]
        ticket_store.ingest(tickets)
        
        results = ticket_store.search_similar("sipariş kargo nerede", limit=2)
        
        assert len(results) <= 2
        # Should find tickets with matching keywords
        subjects = [r.subject for r in results]
        assert any("Sipariş" in s or "Kargo" in s for s in subjects)
    
    def test_load_dummy_fixtures(self):
        """Load dummy fixture file."""
        count = load_dummy_fixtures()
        
        assert count == 6  # We have 6 dummy tickets
        assert ticket_store.count() == 6
    
    def test_get_nonexistent_ticket(self):
        """Getting nonexistent ticket returns None."""
        result = ticket_store.get_by_conversation_id("does-not-exist")
        assert result is None
    
    def test_get_nonexistent_customer(self):
        """Getting tickets for nonexistent customer returns empty list."""
        results = ticket_store.get_by_customer_id("cust_nonexistent")
        assert results == []
