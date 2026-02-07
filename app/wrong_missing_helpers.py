"""
Wrong/Missing Item Helpers - Detection and extraction utilities.
"""
import re
from typing import Optional


def extract_order_number(text: str) -> Optional[str]:
    """
    Extract order number from text (e.g., #1234, ORD-1234, order 1234).
    
    Args:
        text: User message text
        
    Returns:
        Order number with # prefix, or None if not found
    """
    if not text:
        return None
    
    # Pattern 1: #1234 or # 1234
    match = re.search(r'#\s*(\d{4,10})', text)
    if match:
        return f"#{match.group(1)}"
    
    # Pattern 2: ORD-1234 or ORDER-1234
    match = re.search(r'(?:ORD|ORDER)[-_]?(\d{4,10})', text, re.IGNORECASE)
    if match:
        return f"#{match.group(1)}"
    
    # Pattern 3: "order number 1234" or "order 1234"
    match = re.search(r'order\s+(?:number\s+)?(\d{4,10})', text, re.IGNORECASE)
    if match:
        return f"#{match.group(1)}"
    
    return None


def detect_photo_attachment(text: str) -> bool:
    """
    Detect if user indicates they've sent photos.
    
    Args:
        text: User message text
        
    Returns:
        True if photos seem to be attached/sent
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Keywords indicating photo attachment
    keywords = [
        "attached",
        "attaching",
        "here's the photo",
        "here are the photos",
        "sending photo",
        "sent photo",
        "uploaded",
        "see attached",
        "please find",
        "i've attached",
        "i attached",
        "photos attached",
        "picture attached",
        "image attached",
        "[image]",
        "[photo]",
        "[attachment]"
    ]
    
    return any(keyword in text_lower for keyword in keywords)


def detect_wrong_missing_type(text: str) -> Optional[str]:
    """
    Detect if user indicates missing or wrong item.
    
    Args:
        text: User message text
        
    Returns:
        "MISSING_ITEM", "WRONG_ITEM", or None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Missing item indicators
    missing_keywords = [
        "missing",
        "not in the box",
        "wasn't included",
        "not included",
        "didn't receive",
        "didn't get",
        "never received",
        "not in package",
        "empty box",
        "item not there"
    ]
    
    # Wrong item indicators
    wrong_keywords = [
        "wrong item",
        "wrong product",
        "different item",
        "not what i ordered",
        "received different",
        "got the wrong",
        "sent wrong",
        "incorrect item",
        "different product",
        "wrong size",
        "wrong color",
        "wrong colour"
    ]
    
    for keyword in wrong_keywords:
        if keyword in text_lower:
            return "WRONG_ITEM"
    
    for keyword in missing_keywords:
        if keyword in text_lower:
            return "MISSING_ITEM"
    
    return None


def detect_resolution_preference(text: str) -> Optional[str]:
    """
    Detect customer's preferred resolution.
    
    Args:
        text: User message text
        
    Returns:
        "RESHIP", "STORE_CREDIT", "CASH_REFUND", or None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Reship indicators
    reship_keywords = [
        "reship",
        "resend",
        "send again",
        "new one",
        "replacement",
        "send replacement",
        "ship again"
    ]
    
    # Store credit indicators
    credit_keywords = [
        "store credit",
        "credit",
        "bonus"
    ]
    
    # Cash refund indicators
    refund_keywords = [
        "refund",
        "money back",
        "get my money",
        "cash back",
        "original payment"
    ]
    
    # Check in order of preference (reship first as per spec)
    for keyword in reship_keywords:
        if keyword in text_lower:
            return "RESHIP"
    
    for keyword in credit_keywords:
        if keyword in text_lower:
            return "STORE_CREDIT"
    
    for keyword in refund_keywords:
        if keyword in text_lower:
            return "CASH_REFUND"
    
    return None


def detect_acceptance(text: str) -> bool:
    """Detect if user is accepting an offer."""
    if not text:
        return False
    
    text_lower = text.lower()
    accept_keywords = [
        "yes", "ok", "okay", "sure", "fine", "sounds good",
        "that works", "accept", "i'll take", "please do",
        "go ahead", "let's do"
    ]
    return any(keyword in text_lower for keyword in accept_keywords)


def detect_decline(text: str) -> bool:
    """Detect if user is declining an offer."""
    if not text:
        return False
    
    text_lower = text.lower()
    decline_keywords = [
        "no", "nope", "don't want", "prefer not",
        "rather have", "instead", "actually",
        "not interested", "decline"
    ]
    return any(keyword in text_lower for keyword in decline_keywords)
