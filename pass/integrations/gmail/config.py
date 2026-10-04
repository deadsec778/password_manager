import os
from dotenv import load_dotenv

# Load .env from pass/ root (two levels up from integrations/gmail/)
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(ENV_PATH)

# Gmail SMTP Configuration
GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", os.getenv("GMAIL_USER", "")).strip().strip('"').strip("'")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip().strip('"').strip("'").replace(" ", "")
GMAIL_SMTP_HOST = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com").strip().strip('"').strip("'")
GMAIL_SMTP_PORT = int(os.getenv("GMAIL_SMTP_PORT", "587"))
GMAIL_USE_TLS = os.getenv("GMAIL_USE_TLS", "true").lower() in ("true", "1", "yes")
GMAIL_USE_SSL = os.getenv("GMAIL_USE_SSL", "false").lower() in ("true", "1", "yes")

# App Brand Info
APP_NAME = os.getenv("APP_NAME", "DeadSec Password Manager").strip()
APP_URL = os.getenv("APP_URL", "http://127.0.0.1:5000").strip()

# Security & OTP Settings
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
OTP_DIGITS = int(os.getenv("OTP_DIGITS", "6"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))

def is_gmail_enabled() -> bool:
    """Check if Gmail integration is enabled globally and for the Gmail module."""
    try:
        from integrations.config import is_gmail_enabled as _check_gmail
        return _check_gmail()
    except Exception:
        load_dotenv(ENV_PATH)
        master = os.getenv("INTEGRATIONS_ENABLED", "true").lower() in ("true", "1", "yes", "on")
        module_en = os.getenv("GMAIL_INTEGRATION_ENABLED", "true").lower() in ("true", "1", "yes", "on")
        return master and module_en


def is_gmail_configured() -> bool:
    """Check if Gmail SMTP credentials are configured in .env."""
    load_dotenv(ENV_PATH)
    sender = os.getenv("GMAIL_SENDER_EMAIL", os.getenv("GMAIL_USER", "")).strip().strip('"').strip("'")
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip().strip('"').strip("'").replace(" ", "")
    return bool(sender and password)


def is_gmail_active() -> bool:
    """Check if Gmail integration is both enabled and credentials are configured."""
    return is_gmail_enabled() and is_gmail_configured()

