"""
In-memory session store.
Simple dict-based storage - no database required for MVP.
"""
from typing import Optional
from datetime import datetime
from app.models import (
    Session, SessionStatus, CustomerInfo, Message, TraceEvent
)


class SessionStore:
    """
    Thread-safe in-memory session storage.
    For MVP only - data is lost on restart.
    """
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}
    
    def create(self, customer_info: CustomerInfo) -> Session:
        """Create a new session for a customer."""
        session = Session(customer_info=customer_info)
        self._sessions[session.id] = session
        return session
    
    def get(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)
    
    def update(self, session: Session) -> Session:
        """Update an existing session."""
        if session.id not in self._sessions:
            raise ValueError(f"Session {session.id} not found")
        session.updated_at = datetime.utcnow()
        self._sessions[session.id] = session
        return session
    
    def add_message(self, session_id: str, message: Message) -> Session:
        """Add a message to a session."""
        session = self.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.messages.append(message)
        return self.update(session)
    
    def add_trace_event(self, session_id: str, event: TraceEvent) -> Session:
        """Add a trace event to a session."""
        session = self.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.trace.append(event)
        return self.update(session)
    
    def set_status(self, session_id: str, status: SessionStatus) -> Session:
        """Update session status (e.g., to escalated)."""
        session = self.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.status = status
        return self.update(session)
    
    def is_escalated(self, session_id: str) -> bool:
        """Check if a session is in escalated state (locked)."""
        session = self.get(session_id)
        if not session:
            return False
        return session.status == SessionStatus.ESCALATED
    
    def list_all(self) -> list[Session]:
        """List all sessions (for debugging)."""
        return list(self._sessions.values())
    
    def clear(self):
        """Clear all sessions (for testing)."""
        self._sessions.clear()


# Global singleton instance
session_store = SessionStore()
