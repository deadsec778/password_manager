"""
Gmail Integration Package for Password Manager.
Provides SMTP mail delivery, OTP generation & verification,
HTML email rendering, and complete password reset & registration workflows.
"""

from .config import (
    GMAIL_SENDER_EMAIL,
    GMAIL_APP_PASSWORD,
    GMAIL_SMTP_HOST,
    GMAIL_SMTP_PORT,
    APP_NAME,
    APP_URL,
    OTP_EXPIRY_MINUTES,
    is_gmail_configured,
    is_gmail_enabled,
    is_gmail_active,
)
from .email_service import (
    GmailSender,
    default_sender,
    send_registration_otp_email,
    send_password_reset_otp_email,
    send_password_changed_notification,
)
from .otp_manager import (
    OTPManager,
    default_otp_manager,
    ensure_otp_table,
)
from .templates import (
    render_registration_otp_email,
    render_password_reset_otp_email,
    render_password_changed_email,
)

__all__ = [
    "GMAIL_SENDER_EMAIL",
    "GMAIL_APP_PASSWORD",
    "GMAIL_SMTP_HOST",
    "GMAIL_SMTP_PORT",
    "APP_NAME",
    "APP_URL",
    "OTP_EXPIRY_MINUTES",
    "is_gmail_configured",
    "is_gmail_enabled",
    "is_gmail_active",
    "GmailSender",
    "default_sender",
    "send_registration_otp_email",
    "send_password_reset_otp_email",
    "send_password_changed_notification",
    "OTPManager",
    "default_otp_manager",
    "ensure_otp_table",
    "render_registration_otp_email",
    "render_password_reset_otp_email",
    "render_password_changed_email",
]
