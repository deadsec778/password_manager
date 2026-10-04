"""
Integrations Package for Password Manager.
Exposes master toggle controls, feature flag helpers, and modular service integrations.
"""

from .config import (
    is_integrations_master_enabled,
    is_google_oauth_enabled,
    is_gmail_enabled,
    is_feature_enabled,
    get_integrations_status,
)

__all__ = [
    "is_integrations_master_enabled",
    "is_google_oauth_enabled",
    "is_gmail_enabled",
    "is_feature_enabled",
    "get_integrations_status",
]
