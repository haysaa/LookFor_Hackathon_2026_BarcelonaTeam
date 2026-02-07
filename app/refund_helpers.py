"""
Refund Helpers - Computation and detection utilities for refund workflow.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


# Usage tips for expectation causes (static templates, no hallucination)
USAGE_TIPS = {
    "falling_asleep": "For best results with falling asleep, take the product 30-60 minutes before your desired bedtime. Avoid screens and bright lights during this time, and keep your room cool and dark.",
    "staying_asleep": "To help with staying asleep, try taking the product with a small snack. Avoid caffeine after 2pm, and consider using a white noise machine to minimize disruptions.",
    "comfort": "For comfort concerns, try adjusting your sleeping position or pillow height. Our product works best when combined with a consistent bedtime routine.",
    "taste": "If taste is a concern, try mixing with your favorite juice or smoothie. You can also take it with a small amount of honey or follow with a mint.",
    "no_effect": "If you're not noticing effects, ensure you're taking the recommended dosage consistently for at least 2 weeks. Avoid alcohol and heavy meals close to bedtime for best results."
}


def compute_shipping_promise(contact_day: str) -> Tuple[str, str]:
    """
    Compute shipping promise type and deadline based on contact day.
    
    Mon/Tue → wait until Friday
    Wed-Fri → wait until early next week (next Monday)
    
    Args:
        contact_day: Day of week (Mon, Tue, Wed, Thu, Fri, Sat, Sun)
        
    Returns:
        Tuple of (promise_type, deadline_date ISO string)
    """
    today = datetime.now()
    day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    
    current_weekday = today.weekday()
    
    # Override with contact_day if provided
    if contact_day and contact_day in day_map:
        current_weekday = day_map[contact_day]
    
    if current_weekday in [0, 1]:  # Monday or Tuesday
        # Promise Friday of current week
        days_until_friday = 4 - current_weekday
        deadline = today + timedelta(days=days_until_friday)
        return ("FRIDAY", deadline.strftime("%Y-%m-%d"))
    else:
        # Wed-Sun: Promise next Monday
        days_until_monday = (7 - current_weekday) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # If today is Monday, next Monday is 7 days
        deadline = today + timedelta(days=days_until_monday)
        return ("EARLY_NEXT_WEEK", deadline.strftime("%Y-%m-%d"))


def get_usage_tip(expectation_cause: str) -> Optional[str]:
    """
    Get usage tip template for a given expectation cause.
    
    Args:
        expectation_cause: One of falling_asleep, staying_asleep, comfort, taste, no_effect
        
    Returns:
        Usage tip string or None if cause not recognized
    """
    if not expectation_cause:
        return None
    return USAGE_TIPS.get(expectation_cause.lower())


def detect_refund_reason(text: str) -> Optional[str]:
    """
    Detect refund reason from customer message.
    
    Args:
        text: Customer message
        
    Returns:
        EXPECTATIONS | SHIPPING_DELAY | DAMAGED_OR_WRONG | CHANGED_MIND | None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Damaged or wrong item
    damaged_keywords = [
        "damaged", "broken", "wrong item", "wrong product",
        "not what i ordered", "defective", "missing item",
        "incorrect", "received different"
    ]
    for kw in damaged_keywords:
        if kw in text_lower:
            return "DAMAGED_OR_WRONG"
    
    # Shipping delay
    shipping_keywords = [
        "shipping delay", "delayed", "late delivery", "hasn't arrived",
        "still waiting", "where is my order", "not delivered",
        "taking too long", "slow shipping"
    ]
    for kw in shipping_keywords:
        if kw in text_lower:
            return "SHIPPING_DELAY"
    
    # Changed mind
    changed_mind_keywords = [
        "changed my mind", "don't want it", "don't need it",
        "no longer need", "cancel", "changed mind",
        "don't want anymore", "accidentally ordered"
    ]
    for kw in changed_mind_keywords:
        if kw in text_lower:
            return "CHANGED_MIND"
    
    # Product expectations (catch-all for product issues)
    expectations_keywords = [
        "didn't work", "doesn't work", "not working",
        "no effect", "didn't meet expectations", "disappointed",
        "not as expected", "not satisfied", "underwhelming",
        "didn't help", "not effective", "waste of money"
    ]
    for kw in expectations_keywords:
        if kw in text_lower:
            return "EXPECTATIONS"
    
    return None


def detect_expectation_cause(text: str) -> Optional[str]:
    """
    Detect the specific cause for expectation-based refund.
    
    Args:
        text: Customer message
        
    Returns:
        falling_asleep | staying_asleep | comfort | taste | no_effect | None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Falling asleep
    if any(kw in text_lower for kw in ["fall asleep", "falling asleep", "can't sleep", "hard to sleep", "trouble sleeping"]):
        return "falling_asleep"
    
    # Staying asleep
    if any(kw in text_lower for kw in ["stay asleep", "staying asleep", "wake up", "waking up", "interrupted sleep"]):
        return "staying_asleep"
    
    # Comfort
    if any(kw in text_lower for kw in ["comfort", "uncomfortable", "texture", "feel"]):
        return "comfort"
    
    # Taste
    if any(kw in text_lower for kw in ["taste", "flavor", "gross", "bad taste", "nasty"]):
        return "taste"
    
    # No effect (catch-all)
    if any(kw in text_lower for kw in ["no effect", "didn't work", "doesn't work", "not effective", "nothing happened"]):
        return "no_effect"
    
    return None


def detect_wait_acceptance(text: str) -> Optional[str]:
    """
    Detect if customer accepts or declines waiting.
    
    Args:
        text: Customer message
        
    Returns:
        ACCEPTED | DECLINED | None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Acceptance
    accept_keywords = [
        "yes", "ok", "okay", "sure", "fine", "i can wait",
        "i'll wait", "that's fine", "sounds good", "no problem"
    ]
    for kw in accept_keywords:
        if kw in text_lower:
            return "ACCEPTED"
    
    # Decline
    decline_keywords = [
        "no", "can't wait", "don't want to wait", "not acceptable",
        "too long", "need it now", "unacceptable", "refund now",
        "immediately", "right now"
    ]
    for kw in decline_keywords:
        if kw in text_lower:
            return "DECLINED"
    
    return None


def detect_resolution_choice(text: str) -> Optional[str]:
    """
    Detect customer's resolution choice.
    
    Args:
        text: Customer message
        
    Returns:
        REPLACEMENT | STORE_CREDIT | REFUND | SWAP | None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Replacement
    if any(kw in text_lower for kw in ["replace", "replacement", "new one", "send another", "reship"]):
        return "REPLACEMENT"
    
    # Swap
    if any(kw in text_lower for kw in ["swap", "exchange", "different product", "try something else"]):
        return "SWAP"
    
    # Store credit
    if any(kw in text_lower for kw in ["store credit", "credit"]):
        return "STORE_CREDIT"
    
    # Refund
    if any(kw in text_lower for kw in ["refund", "money back", "cash back", "original payment"]):
        return "REFUND"
    
    return None


def is_shipping_promise_passed(deadline_date: str) -> bool:
    """
    Check if shipping promise deadline has passed.
    
    Args:
        deadline_date: ISO date string (YYYY-MM-DD)
        
    Returns:
        True if deadline has passed
    """
    if not deadline_date:
        return False
    
    try:
        deadline = datetime.strptime(deadline_date, "%Y-%m-%d").date()
        return datetime.now().date() > deadline
    except ValueError:
        return False
