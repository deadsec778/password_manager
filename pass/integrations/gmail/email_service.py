"""
Gmail SMTP Email Service.
Handles connection, authentication with Google App Passwords,
and sending multipart MIME HTML/Plaintext emails.
"""

import smtplib
import ssl
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple

from .config import (
    GMAIL_SENDER_EMAIL,
    GMAIL_APP_PASSWORD,
    GMAIL_SMTP_HOST,
    GMAIL_SMTP_PORT,
    GMAIL_USE_TLS,
    GMAIL_USE_SSL,
    APP_NAME,
    is_gmail_configured,
    is_gmail_enabled,
    OTP_EXPIRY_MINUTES,
)
from .templates import (
    render_registration_otp_email,
    render_password_reset_otp_email,
    render_password_changed_email,
)

logger = logging.getLogger("gmail_service")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def _get_current_credentials() -> Tuple[str, str, str, int]:
    """Dynamically read current credentials from environment."""
    from dotenv import load_dotenv
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    load_dotenv(env_path)

    sender = os.getenv("GMAIL_SENDER_EMAIL", os.getenv("GMAIL_USER", "")).strip().strip('"').strip("'")
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip().strip('"').strip("'").replace(" ", "")
    host = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com").strip().strip('"').strip("'")
    port = int(os.getenv("GMAIL_SMTP_PORT", "587"))
    return sender, password, host, port


class GmailSender:
    """Encapsulates Gmail SMTP transmission and error handling."""

    def __init__(
        self,
        sender_email: Optional[str] = None,
        app_password: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self._custom_sender = sender_email
        self._custom_password = app_password
        self._custom_host = host
        self._custom_port = port

    def get_config(self) -> Tuple[str, str, str, int]:
        dyn_sender, dyn_pw, dyn_host, dyn_port = _get_current_credentials()
        sender = self._custom_sender or dyn_sender
        pw = (self._custom_password.replace(" ", "") if self._custom_password else None) or dyn_pw
        host = self._custom_host or dyn_host
        port = self._custom_port or dyn_port
        return sender, pw, host, port

    def is_ready(self) -> bool:
        if not is_gmail_enabled():
            return False
        sender, pw, _, _ = self.get_config()
        return bool(sender and pw)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Sends an email using Gmail SMTP with automatic TLS/SSL fallback.
        """
        if not is_gmail_enabled():
            err = "Gmail integration is disabled in configuration."
            logger.info(err)
            return False, err

        to_email = to_email.strip().lower()
        if not to_email:
            return False, "Recipient email address is required."

        sender, password, host, port = self.get_config()

        if not sender or not password:
            err = "Gmail SMTP credentials not configured in .env (GMAIL_SENDER_EMAIL, GMAIL_APP_PASSWORD)."
            logger.error(err)
            return False, err

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{APP_NAME} <{sender}>"
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        if html_content:
            msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Strategy: Try configured port first, fallback if network/socket issue occurs
        ports_to_try = [port]
        if port == 587 and 465 not in ports_to_try:
            ports_to_try.append(465)
        elif port == 465 and 587 not in ports_to_try:
            ports_to_try.append(587)

        last_error = ""

        for current_port in ports_to_try:
            try:
                context = ssl.create_default_context()
                if current_port == 465:
                    server = smtplib.SMTP_SSL(host, 465, context=context, timeout=15)
                else:
                    server = smtplib.SMTP(host, 587, timeout=15)
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()

                server.login(sender, password)
                server.sendmail(sender, [to_email], msg.as_string())
                server.quit()

                logger.info(f"Successfully sent email '{subject}' to {to_email} via {host}:{current_port}")
                return True, "Email sent successfully."

            except smtplib.SMTPAuthenticationError as auth_err:
                last_error = (
                    f"Gmail authentication failed (535 Bad Credentials). "
                    f"Please verify GMAIL_SENDER_EMAIL ({sender}) and 16-digit Google App Password in .env. "
                    f"Error: {auth_err}"
                )
                logger.error(last_error)
                # Auth error won't change on different port
                return False, last_error
            except Exception as e:
                last_error = f"Error sending via {host}:{current_port} -> {str(e)}"
                logger.warning(last_error)

        return False, f"Failed to send email to {to_email}: {last_error}"


# Global default sender instance
default_sender = GmailSender()


def send_registration_otp_email(
    to_email: str,
    username: str,
    otp_code: str,
    expiry_minutes: int = OTP_EXPIRY_MINUTES,
) -> Tuple[bool, str]:
    """Sends the registration OTP code to a new user for account verification."""
    html_body, text_body = render_registration_otp_email(username, otp_code, expiry_minutes)
    subject = f"{otp_code} is your {APP_NAME} verification code"
    return default_sender.send_email(to_email, subject, html_body, text_body)


def send_password_reset_otp_email(
    to_email: str,
    username: str,
    otp_code: str,
    expiry_minutes: int = OTP_EXPIRY_MINUTES,
) -> Tuple[bool, str]:
    """Sends the password reset / one-time login OTP code to an existing user."""
    html_body, text_body = render_password_reset_otp_email(username, otp_code, expiry_minutes)
    subject = f"{otp_code} is your {APP_NAME} security code"
    return default_sender.send_email(to_email, subject, html_body, text_body)


def send_password_changed_notification(
    to_email: str,
    username: str,
) -> Tuple[bool, str]:
    """Sends a security alert notification when a password was updated."""
    html_body, text_body = render_password_changed_email(username)
    subject = f"Security Alert: Password Changed - {APP_NAME}"
    return default_sender.send_email(to_email, subject, html_body, text_body)
