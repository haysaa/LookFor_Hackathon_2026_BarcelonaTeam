"""
Configuration Management
Version: 1.0

Centralized configuration for the multi-agent system.
Uses environment variables with sensible defaults.
"""
import os
from typing import Literal

# Language Configuration
RESPONSE_LANGUAGE: Literal["tr", "en"] = os.getenv("RESPONSE_LANGUAGE", "tr").lower()
BRAND_TONE: str = os.getenv("BRAND_TONE", "empathetic_professional")

# Triage Agent Configuration
TRIAGE_CONFIDENCE_THRESHOLD: float = float(os.getenv("TRIAGE_CONFIDENCE_THRESHOLD", "0.6"))
TRIAGE_LOW_CONFIDENCE_ACTION: Literal["ask_clarifying", "escalate"] = os.getenv(
    "TRIAGE_LOW_CONFIDENCE_ACTION", "ask_clarifying"
)

# Tool Configuration
TOOL_MAX_RETRIES: int = int(os.getenv("TOOL_MAX_RETRIES", "1"))
TOOL_FAILURE_THRESHOLD: int = int(os.getenv("TOOL_FAILURE_THRESHOLD", "2"))

# Escalation Configuration
AUTO_ESCALATE_ON_TOOL_FAILURE: bool = os.getenv("AUTO_ESCALATE_ON_TOOL_FAILURE", "true").lower() == "true"
AUTO_ESCALATE_ON_LOW_CONFIDENCE: bool = os.getenv("AUTO_ESCALATE_ON_LOW_CONFIDENCE", "false").lower() == "true"

# Language Templates
FALLBACK_MESSAGES = {
    "tr": {
        "tool_failure": "Üzgünüz, sisteminizde geçici bir sorun yaşıyoruz. Talebiniz uzman ekibimize iletildi. 24 saat içinde size dönüş yapacağız.",
        "low_confidence": "Talebinizi tam olarak anlayabilmek için birkaç ek bilgiye ihtiyacım var. Lütfen sorunuzu biraz daha detaylandırabilir misiniz?",
        "general_error": "Beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin veya destek ekibimizle iletişime geçin.",
        "escalated": "Talebiniz özel destek ekibimize iletildi. Uzmanlarımız en kısa sürede size dönüş yapacaktır."
    },
    "en": {
        "tool_failure": "We're sorry, we're experiencing a temporary issue with our system. Your request has been forwarded to our specialist team. We'll get back to you within 24 hours.",
        "low_confidence": "To better assist you, I need a bit more information. Could you please provide more details about your request?",
        "general_error": "An unexpected error occurred. Please try again later or contact our support team.",
        "escalated": "Your request has been forwarded to our specialist team. Our experts will get back to you shortly."
    }
}


def get_fallback_message(message_type: str, language: str = None) -> str:
    """
    Get fallback message for a given type.
    
    Args:
        message_type: Type of message (tool_failure, low_confidence, etc.)
        language: Language code (defaults to RESPONSE_LANGUAGE)
    
    Returns:
        Localized fallback message
    """
    lang = language or RESPONSE_LANGUAGE
    messages = FALLBACK_MESSAGES.get(lang, FALLBACK_MESSAGES["en"])
    return messages.get(message_type, messages["general_error"])


# Configuration validation
def validate_config():
    """Validate configuration values."""
    errors = []
    
    if RESPONSE_LANGUAGE not in ["tr", "en"]:
        errors.append(f"Invalid RESPONSE_LANGUAGE: {RESPONSE_LANGUAGE}")
    
    if not 0 < TRIAGE_CONFIDENCE_THRESHOLD <= 1:
        errors.append(f"TRIAGE_CONFIDENCE_THRESHOLD must be between 0 and 1: {TRIAGE_CONFIDENCE_THRESHOLD}")
    
    if TRIAGE_LOW_CONFIDENCE_ACTION not in ["ask_clarifying", "escalate"]:
        errors.append(f"Invalid TRIAGE_LOW_CONFIDENCE_ACTION: {TRIAGE_LOW_CONFIDENCE_ACTION}")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True


# Auto-validate on import
validate_config()
