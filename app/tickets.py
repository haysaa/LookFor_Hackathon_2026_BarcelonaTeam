"""
TicketStore - Interface for ticket dataset management.
Handles storage and retrieval of customer support tickets.
Supports both dummy (fixtures) and real (anonymized) ticket formats.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import os
import re
import hashlib


# ============================================================================
# Canonical Ticket Model
# ============================================================================

class TicketRecord(BaseModel):
    """
    Canonical ticket representation supporting both real and dummy formats.
    Used internally for storage and search.
    """
    id: str                                # conversationId or generated hash
    customer_id: Optional[str] = None
    created_at: Optional[datetime] = None
    channel: str = "email"                 # from conversationType
    subject: Optional[str] = None
    raw_conversation: str = ""
    turns: list[dict] = Field(default_factory=list)  # [{role, text}]
    tokens: set[str] = Field(default_factory=set)    # keywords for search
    
    class Config:
        arbitrary_types_allowed = True


class Ticket(BaseModel):
    """
    Legacy ticket data model matching hackathon format.
    Kept for backwards compatibility with existing code.
    """
    conversation_id: str = Field(alias="conversationId")
    customer_id: str = Field(alias="customerId")
    created_at: str = Field(alias="createdAt")
    conversation_type: str = Field(default="email", alias="ConversationType")
    subject: str
    conversation: str
    
    class Config:
        populate_by_name = True


# ============================================================================
# Parsing Functions
# ============================================================================

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date string in various formats.
    Handles: "19-Jul-2025 14:58:48", "03-Feb-2026 10:30:00", etc.
    Returns None on failure (graceful handling).
    """
    if not date_str:
        return None
    
    formats = [
        "%d-%b-%Y %H:%M:%S",    # 19-Jul-2025 14:58:48
        "%Y-%m-%dT%H:%M:%S",    # ISO format
        "%Y-%m-%d %H:%M:%S",    # Standard
        "%d/%m/%Y %H:%M:%S",    # European
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def parse_conversation_to_turns(text: str) -> list[dict]:
    """
    Parse conversation text into structured turns.
    
    Splits using markers:
    - "Customer's message:" / "Customer's message :"
    - "Agent's message:" / "Agent's message :"
    
    Returns list of {role: "customer"|"agent", text: str}
    """
    if not text:
        return []
    
    # Pattern to split on Customer's/Agent's message markers
    # Handles variations like "Customer's message:" or "Customer's message :"
    pattern = r"(Customer'?s?\s+message\s*:|Agent'?s?\s+message\s*:)"
    
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    
    turns = []
    current_role = None
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Check if this is a marker
        lower = part.lower()
        if "customer" in lower and "message" in lower:
            current_role = "customer"
        elif "agent" in lower and "message" in lower:
            current_role = "agent"
        elif current_role:
            # This is content for the current role
            turns.append({
                "role": current_role,
                "text": part
            })
    
    # If no markers found, treat entire text as single customer message
    if not turns and text.strip():
        turns.append({
            "role": "customer",
            "text": text.strip()
        })
    
    return turns


def tokenize(text: str, min_length: int = 3) -> set[str]:
    """
    Tokenize text for keyword-based search.
    
    - Lowercase
    - Split on non-alphanumeric
    - Drop tokens shorter than min_length
    """
    if not text:
        return set()
    
    # Split on non-alphanumeric characters
    words = re.split(r'[^a-zA-Z0-9]+', text.lower())
    
    # Filter short tokens and common stop words
    stop_words = {'the', 'and', 'for', 'are', 'was', 'is', 'in', 'to', 'of', 'a', 'an'}
    
    return {w for w in words if len(w) >= min_length and w not in stop_words}


def generate_ticket_id(obj: dict) -> str:
    """Generate stable hash ID if conversationId not available."""
    content = json.dumps(obj, sort_keys=True)
    return f"ticket_{hashlib.md5(content.encode()).hexdigest()[:12]}"


def parse_real_ticket(obj: dict) -> TicketRecord:
    """
    Parse ticket from real anonymized format.
    
    Expected fields:
    - conversationId
    - customerId
    - createdAt (e.g., "19-Jul-2025 14:58:48")
    - conversationType
    - subject
    - conversation (with "Customer's message:" / "Agent's message:" markers)
    """
    raw_conversation = obj.get("conversation", "")
    turns = parse_conversation_to_turns(raw_conversation)
    
    # Build tokens from subject + customer turns
    token_source = obj.get("subject", "") or ""
    for turn in turns:
        if turn.get("role") == "customer":
            token_source += " " + turn.get("text", "")
    
    return TicketRecord(
        id=obj.get("conversationId") or generate_ticket_id(obj),
        customer_id=obj.get("customerId"),
        created_at=parse_date(obj.get("createdAt", "")),
        channel=obj.get("conversationType", "email"),
        subject=obj.get("subject"),
        raw_conversation=raw_conversation,
        turns=turns,
        tokens=tokenize(token_source)
    )


def parse_dummy_ticket(obj: dict) -> TicketRecord:
    """
    Parse ticket from dummy fixtures format.
    
    Expected fields (same as real but conversation is plain text):
    - conversationId
    - customerId
    - createdAt
    - ConversationType
    - subject
    - conversation (plain text, no markers)
    """
    raw_conversation = obj.get("conversation", "")
    
    # Dummy format: conversation is usually single customer message
    turns = parse_conversation_to_turns(raw_conversation)
    
    # Build tokens
    token_source = obj.get("subject", "") or ""
    token_source += " " + raw_conversation
    
    return TicketRecord(
        id=obj.get("conversationId") or generate_ticket_id(obj),
        customer_id=obj.get("customerId"),
        created_at=parse_date(obj.get("createdAt", "")),
        channel=obj.get("ConversationType", obj.get("conversationType", "email")),
        subject=obj.get("subject"),
        raw_conversation=raw_conversation,
        turns=turns,
        tokens=tokenize(token_source)
    )


def detect_ticket_format(data: list[dict]) -> str:
    """
    Auto-detect whether data is real or dummy format.
    
    Real format: has "conversation" with "Customer's message:" markers
    Dummy format: plain text conversation
    """
    if not data:
        return "dummy"
    
    # Check first few tickets
    for obj in data[:5]:
        conv = obj.get("conversation", "")
        if "Customer's message" in conv or "Agent's message" in conv:
            return "real"
    
    return "dummy"


# ============================================================================
# TicketStore
# ============================================================================

class TicketStore:
    """
    In-memory ticket store with search capabilities.
    Supports both dummy and real ticket formats.
    Designed for hackathon MVP - can be replaced with DB later.
    """
    
    def __init__(self):
        self._records: dict[str, TicketRecord] = {}
        self._by_customer: dict[str, list[str]] = {}
        # Legacy storage for backwards compatibility
        self._tickets: dict[str, Ticket] = {}
    
    def load_from_json(self, path: str) -> int:
        """
        Load tickets from JSON file with auto-detection.
        
        Supports:
        - Real format (with Customer's/Agent's message markers)
        - Dummy format (plain text)
        
        Returns number of tickets loaded.
        
        Note: For real tickets, copy the file to fixtures/tickets_real.json
        or set TICKETS_PATH environment variable to the file path.
        """
        if not os.path.exists(path):
            print(f"TicketStore: File not found: {path}")
            return 0
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"TicketStore: Failed to load {path}: {e}")
            return 0
        
        if not isinstance(data, list):
            print(f"TicketStore: Expected JSON array, got {type(data)}")
            return 0
        
        # Auto-detect format
        format_type = detect_ticket_format(data)
        parser = parse_real_ticket if format_type == "real" else parse_dummy_ticket
        
        # Parse and dedupe
        seen_ids = set()
        loaded = 0
        duplicates = 0
        
        for obj in data:
            try:
                record = parser(obj)
                
                # Dedup by ID
                if record.id in seen_ids:
                    duplicates += 1
                    continue
                
                seen_ids.add(record.id)
                self._records[record.id] = record
                
                # Index by customer
                if record.customer_id:
                    if record.customer_id not in self._by_customer:
                        self._by_customer[record.customer_id] = []
                    self._by_customer[record.customer_id].append(record.id)
                
                loaded += 1
                
            except Exception as e:
                print(f"TicketStore: Failed to parse ticket: {e}")
        
        print(f"TicketStore: Loaded {loaded} tickets ({format_type} format), {duplicates} duplicates skipped")
        return loaded
    
    def get_by_conversation_id(self, conv_id: str) -> Optional[TicketRecord]:
        """Get a ticket by its conversation ID."""
        return self._records.get(conv_id)
    
    def get_by_customer_id(self, customer_id: str) -> list[TicketRecord]:
        """Get all tickets for a customer."""
        ticket_ids = self._by_customer.get(customer_id, [])
        return [self._records[tid] for tid in ticket_ids if tid in self._records]
    
    def search_similar(self, query: str, limit: int = 3) -> list[TicketRecord]:
        """
        Token-overlap based search for similar tickets.
        Used for RAG in SupportAgent.
        
        Scoring: count of overlapping tokens between query and ticket.
        Returns top-k TicketRecord objects.
        """
        query_tokens = tokenize(query)
        
        if not query_tokens:
            return []
        
        scored = []
        
        for record in self._records.values():
            # Calculate token overlap
            overlap = len(query_tokens & record.tokens)
            
            if overlap > 0:
                scored.append((overlap, record))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [record for _, record in scored[:limit]]
    
    def ingest(self, tickets: list[dict]) -> int:
        """
        Legacy method: Ingest tickets from JSON array.
        Kept for backwards compatibility.
        Returns number of tickets ingested.
        """
        count = 0
        for ticket_data in tickets:
            try:
                # Parse to TicketRecord
                record = parse_dummy_ticket(ticket_data)
                self._records[record.id] = record
                
                # Index by customer
                if record.customer_id:
                    if record.customer_id not in self._by_customer:
                        self._by_customer[record.customer_id] = []
                    self._by_customer[record.customer_id].append(record.id)
                
                # Also maintain legacy Ticket objects
                try:
                    ticket = Ticket(**ticket_data)
                    self._tickets[ticket.conversation_id] = ticket
                except Exception:
                    pass
                
                count += 1
            except Exception as e:
                print(f"Failed to ingest ticket: {e}")
        
        return count
    
    def ingest_from_file(self, filepath: str) -> int:
        """
        Legacy method: Load tickets from a JSON file.
        Now delegates to load_from_json for unified handling.
        """
        return self.load_from_json(filepath)
    
    def count(self) -> int:
        """Get total ticket count."""
        return len(self._records)
    
    def clear(self):
        """Clear all tickets (for testing)."""
        self._records.clear()
        self._by_customer.clear()
        self._tickets.clear()
    
    def get_all_records(self) -> list[TicketRecord]:
        """Get all ticket records (for debugging/testing)."""
        return list(self._records.values())


# Global singleton instance
ticket_store = TicketStore()


def load_dummy_fixtures() -> int:
    """Load dummy fixtures for development/testing."""
    fixtures_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'fixtures', 
        'tickets_dummy.json'
    )
    return ticket_store.load_from_json(fixtures_path)


def load_tickets_from_config() -> int:
    """
    Load tickets based on TICKETS_PATH environment variable.
    Falls back to dummy fixtures if not set or file not found.
    
    Usage:
        set TICKETS_PATH=fixtures/tickets_real.json
        python main.py
    """
    tickets_path = os.getenv("TICKETS_PATH")
    
    if tickets_path and os.path.exists(tickets_path):
        count = ticket_store.load_from_json(tickets_path)
        if count > 0:
            print(f"Loaded {count} tickets from TICKETS_PATH: {tickets_path}")
            return count
        print(f"Failed to load from TICKETS_PATH, falling back to dummy fixtures")
    
    # Fallback to dummy
    count = load_dummy_fixtures()
    print(f"Loaded {count} dummy tickets (fallback)")
    return count
