"""
TicketStore - Interface for ticket dataset management.
Handles storage and retrieval of customer support tickets.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import os


class Ticket(BaseModel):
    """Ticket data model matching hackathon format."""
    conversation_id: str = Field(alias="conversationId")
    customer_id: str = Field(alias="customerId")
    created_at: str = Field(alias="createdAt")
    conversation_type: str = Field(default="email", alias="ConversationType")
    subject: str
    conversation: str
    
    class Config:
        populate_by_name = True


class TicketStore:
    """
    In-memory ticket store with search capabilities.
    Designed for hackathon MVP - can be replaced with DB later.
    """
    
    def __init__(self):
        self._tickets: dict[str, Ticket] = {}
        self._by_customer: dict[str, list[str]] = {}
    
    def get_by_conversation_id(self, conv_id: str) -> Optional[Ticket]:
        """Get a ticket by its conversation ID."""
        return self._tickets.get(conv_id)
    
    def get_by_customer_id(self, customer_id: str) -> list[Ticket]:
        """Get all tickets for a customer."""
        ticket_ids = self._by_customer.get(customer_id, [])
        return [self._tickets[tid] for tid in ticket_ids if tid in self._tickets]
    
    def search_similar(self, query: str, limit: int = 3) -> list[Ticket]:
        """
        Simple keyword-based search for similar tickets.
        Used for RAG in SupportAgent.
        """
        query_lower = query.lower()
        scored = []
        
        for ticket in self._tickets.values():
            score = 0
            text = f"{ticket.subject} {ticket.conversation}".lower()
            
            # Simple keyword matching
            for word in query_lower.split():
                if len(word) > 3 and word in text:
                    score += 1
            
            if score > 0:
                scored.append((score, ticket))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:limit]]
    
    def ingest(self, tickets: list[dict]) -> int:
        """
        Ingest tickets from JSON array.
        Returns number of tickets ingested.
        """
        count = 0
        for ticket_data in tickets:
            try:
                ticket = Ticket(**ticket_data)
                self._tickets[ticket.conversation_id] = ticket
                
                # Index by customer
                if ticket.customer_id not in self._by_customer:
                    self._by_customer[ticket.customer_id] = []
                self._by_customer[ticket.customer_id].append(ticket.conversation_id)
                
                count += 1
            except Exception as e:
                print(f"Failed to ingest ticket: {e}")
        
        return count
    
    def ingest_from_file(self, filepath: str) -> int:
        """Load tickets from a JSON file."""
        if not os.path.exists(filepath):
            return 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self.ingest(data)
    
    def count(self) -> int:
        """Get total ticket count."""
        return len(self._tickets)
    
    def clear(self):
        """Clear all tickets (for testing)."""
        self._tickets.clear()
        self._by_customer.clear()


# Global singleton instance
ticket_store = TicketStore()


def load_dummy_fixtures():
    """Load dummy fixtures for development/testing."""
    fixtures_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'fixtures', 
        'tickets_dummy.json'
    )
    return ticket_store.ingest_from_file(fixtures_path)
