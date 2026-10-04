"""
Integrations Master Configuration & Feature Flag Registry.
Provides global and per-module toggle controls to enable or disable
external cloud/third-party service integrations (Google OAuth, Gmail SMTP, etc.),
allowing the application to run completely locally in LAN/offline mode.
"""

import os
from typing import Any, Dict
from dotenv import load_dotenv

ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(ENV_PATH)


def _to_bool(val: Any, default: bool = True) -> bool:
    """Safely convert environment variable strings to boolean."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    val_str = str(val).strip().lower()
    if val_str in ("1", "true", "yes", "on", "enabled"):
        return True
    if val_str in ("0", "false", "no", "off", "disabled"):
        return False
    return default


def is_integrations_master_enabled() -> bool:
    """
    Master switch for all external integrations and cloud services.
    Set INTEGRATIONS_ENABLED=false in .env to disable all external integrations
    and run in local-only / LAN mode.
    """
    return _to_bool(os.getenv("INTEGRATIONS_ENABLED", "true"), default=True)


def is_google_oauth_enabled() -> bool:
    """
    Check if Google OAuth integration is enabled.
    Requires master INTEGRATIONS_ENABLED to be true AND GOOGLE_OAUTH_ENABLED to be true.
    """
    if not is_integrations_master_enabled():
        return False
    return _to_bool(os.getenv("GOOGLE_OAUTH_ENABLED", "true"), default=True)


def is_gmail_enabled() -> bool:
    """
    Check if Gmail SMTP & Email OTP integration is enabled.
    Requires master INTEGRATIONS_ENABLED to be true AND GMAIL_INTEGRATION_ENABLED to be true.
    """
    if not is_integrations_master_enabled():
        return False
    return _to_bool(os.getenv("GMAIL_INTEGRATION_ENABLED", "true"), default=True)


def is_feature_enabled(feature_name: str, default: bool = True) -> bool:
    """
    Generic feature flag checker for any existing or future integration module
    (e.g., 'discord', 'telegram', 'slack', 'ldap', 's3_backup').
    
    Checks:
    1. Master INTEGRATIONS_ENABLED (if False, always returns False).
    2. Specific {FEATURE_NAME}_INTEGRATION_ENABLED or {FEATURE_NAME}_ENABLED env var.
    """
    if not is_integrations_master_enabled():
        return False

    feature_clean = feature_name.strip().upper().replace(" ", "_").replace("-", "_")

    # Check MODULE_INTEGRATION_ENABLED
    var_1 = f"{feature_clean}_INTEGRATION_ENABLED"
    if var_1 in os.environ:
        return _to_bool(os.getenv(var_1), default=default)

    # Check MODULE_ENABLED
    var_2 = f"{feature_clean}_ENABLED"
    if var_2 in os.environ:
        return _to_bool(os.getenv(var_2), default=default)

    return default


def get_integrations_status() -> Dict[str, Any]:
    """
    Returns a comprehensive status dictionary of all integrations
    for administrative diagnostics and dashboard health views.
    """
    master = is_integrations_master_enabled()
    google_enabled = is_google_oauth_enabled()
    gmail_enabled = is_gmail_enabled()

    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    google_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    google_configured = bool(google_client_id and google_secret)

    gmail_sender = os.getenv("GMAIL_SENDER_EMAIL", "").strip()
    gmail_pw = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    gmail_configured = bool(gmail_sender and gmail_pw)

    return {
        "master_enabled": master,
        "mode": "hybrid/cloud" if master else "local_lan_only",
        "modules": {
            "google_oauth": {
                "name": "Google OAuth SSO",
                "enabled": google_enabled,
                "configured": google_configured,
                "active": google_enabled and google_configured,
            },
            "gmail_smtp": {
                "name": "Gmail SMTP & Email OTP",
                "enabled": gmail_enabled,
                "configured": gmail_configured,
                "active": gmail_enabled and gmail_configured,
            },
        },
    }
