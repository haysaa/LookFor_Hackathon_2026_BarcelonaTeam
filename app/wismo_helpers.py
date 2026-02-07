"""
WISMO Helpers - Date-based promise logic for shipping delay workflow.
Computes contact day and delivery promise deadlines.
"""
from datetime import datetime, timedelta
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def get_contact_day(session) -> str:
    """
    Get the day of week when customer first contacted.
    
    Args:
        session: Session object with messages list
        
    Returns:
        Day abbreviation: "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"
    """
    # Try to get from session's case_context first (cached)
    if hasattr(session, 'case_context') and session.case_context.contact_day:
        return session.case_context.contact_day
    
    # Get timestamp from first customer message
    contact_time = None
    if hasattr(session, 'messages') and session.messages:
        for msg in session.messages:
            if hasattr(msg, 'role') and str(msg.role.value) == 'customer':
                contact_time = msg.timestamp
                break
    
    # Fallback to session creation time
    if not contact_time:
        contact_time = getattr(session, 'created_at', None)
    
    # Final fallback to now
    if not contact_time:
        contact_time = datetime.utcnow()
        logger.warning("WISMO: Could not determine contact time, using current time")
    
    # Convert to day abbreviation
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return days[contact_time.weekday()]


def compute_promise_deadline(contact_day: str, reference_date: Optional[datetime] = None) -> Tuple[str, str]:
    """
    Compute promise type and deadline date based on contact day.
    
    Args:
        contact_day: Day abbreviation ("Mon", "Tue", etc.)
        reference_date: Reference date (defaults to today)
        
    Returns:
        Tuple of (promise_type, deadline_iso_date)
        - promise_type: "FRIDAY" or "EARLY_NEXT_WEEK"
        - deadline_iso_date: ISO format date string (YYYY-MM-DD)
    """
    if reference_date is None:
        reference_date = datetime.utcnow()
    
    # Map day names to weekday numbers
    day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    
    contact_weekday = day_map.get(contact_day)
    if contact_weekday is None:
        # Invalid day - default to conservative approach
        logger.warning(f"WISMO: Invalid contact_day '{contact_day}', defaulting to EARLY_NEXT_WEEK")
        contact_weekday = 4  # Treat as Friday → next week
    
    current_weekday = reference_date.weekday()
    
    # Mon-Wed (0-2): Promise until Friday
    if contact_weekday <= 2:
        # Calculate days until Friday (weekday 4)
        days_until_friday = (4 - current_weekday) % 7
        if days_until_friday == 0 and current_weekday == 4:
            days_until_friday = 0  # Today is Friday
        deadline = reference_date + timedelta(days=days_until_friday)
        return ("FRIDAY", deadline.strftime("%Y-%m-%d"))
    
    # Thu-Sun (3-6): Promise until early next week (Monday)
    else:
        # Calculate days until next Monday
        days_until_monday = (7 - current_weekday) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # Next Monday, not today
        deadline = reference_date + timedelta(days=days_until_monday)
        return ("EARLY_NEXT_WEEK", deadline.strftime("%Y-%m-%d"))


def is_promise_deadline_passed(deadline_date: str, check_date: Optional[datetime] = None) -> bool:
    """
    Check if the promise deadline has passed.
    
    Args:
        deadline_date: ISO format date string (YYYY-MM-DD)
        check_date: Date to check against (defaults to today)
        
    Returns:
        True if deadline has passed, False otherwise
    """
    if not deadline_date:
        return False
    
    if check_date is None:
        check_date = datetime.utcnow()
    
    try:
        deadline = datetime.strptime(deadline_date, "%Y-%m-%d")
        # Deadline passes at end of day, so check if we're past that date
        return check_date.date() > deadline.date()
    except ValueError:
        logger.error(f"WISMO: Invalid deadline_date format: {deadline_date}")
        return False


def get_promise_message(promise_type: str) -> str:
    """
    Get customer-facing message template for promise type.
    
    Args:
        promise_type: "FRIDAY" or "EARLY_NEXT_WEEK"
        
    Returns:
        Message template string
    """
    if promise_type == "FRIDAY":
        return (
            "Your order is on its way! Based on current shipping updates, "
            "your package should arrive by Friday. If it doesn't arrive by then, "
            "please let us know and we'll arrange a free resend for you."
        )
    else:
        return (
            "Your order is on its way! Based on current shipping updates, "
            "your package should arrive early next week. If it doesn't arrive by then, "
            "please let us know and we'll arrange a free resend for you."
        )


def normalize_shipping_status(raw_status: str) -> str:
    """
    Normalize various shipping status strings to canonical values.
    
    Args:
        raw_status: Raw status from Shopify/carrier
        
    Returns:
        Normalized status: "unfulfilled", "in_transit", "delivered", or "unknown"
    """
    if not raw_status:
        return "unknown"
    
    status_lower = raw_status.lower().strip()
    
    # Delivered variants
    if status_lower in ["delivered", "complete", "completed"]:
        return "delivered"
    
    # Unfulfilled variants
    if status_lower in ["unfulfilled", "pending", "awaiting_fulfillment", "processing"]:
        return "unfulfilled"
    
    # In transit variants
    if status_lower in ["in_transit", "shipped", "fulfilled", "out_for_delivery", "in transit"]:
        return "in_transit"
    
    return "unknown"
