import os
import sys
from unittest.mock import patch, MagicMock
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from integrations import (
    is_integrations_master_enabled,
    is_google_oauth_enabled,
    is_gmail_enabled,
    is_feature_enabled,
    get_integrations_status,
)
from integrations.gmail import (
    is_gmail_configured,
    is_gmail_active,
    send_registration_otp_email,
)
from api.dashboard_app import app


def test_master_switch_disables_all_modules():
    """Verify that INTEGRATIONS_ENABLED=false disables everything."""
    with patch.dict(os.environ, {"INTEGRATIONS_ENABLED": "false", "GOOGLE_OAUTH_ENABLED": "true", "GMAIL_INTEGRATION_ENABLED": "true"}):
        assert is_integrations_master_enabled() is False
        assert is_google_oauth_enabled() is False
        assert is_gmail_enabled() is False
        assert is_feature_enabled("discord") is False
        assert is_feature_enabled("telegram") is False

        status = get_integrations_status()
        assert status["master_enabled"] is False
        assert status["mode"] == "local_lan_only"
        assert status["modules"]["google_oauth"]["enabled"] is False
        assert status["modules"]["gmail_smtp"]["enabled"] is False


def test_granular_google_switch():
    """Verify that Google OAuth can be individually toggled."""
    with patch.dict(os.environ, {"INTEGRATIONS_ENABLED": "true", "GOOGLE_OAUTH_ENABLED": "false", "GMAIL_INTEGRATION_ENABLED": "true"}):
        assert is_integrations_master_enabled() is True
        assert is_google_oauth_enabled() is False
        assert is_gmail_enabled() is True


def test_granular_gmail_switch():
    """Verify that Gmail SMTP can be individually toggled."""
    with patch.dict(os.environ, {"INTEGRATIONS_ENABLED": "true", "GOOGLE_OAUTH_ENABLED": "true", "GMAIL_INTEGRATION_ENABLED": "false"}):
        assert is_integrations_master_enabled() is True
        assert is_google_oauth_enabled() is True
        assert is_gmail_enabled() is False
        assert is_gmail_active() is False


def test_future_module_extensibility():
    """Verify that arbitrary future modules can be queried dynamically."""
    with patch.dict(os.environ, {
        "INTEGRATIONS_ENABLED": "true",
        "DISCORD_INTEGRATION_ENABLED": "true",
        "TELEGRAM_INTEGRATION_ENABLED": "false",
        "LDAP_ENABLED": "true"
    }):
        assert is_feature_enabled("discord") is True
        assert is_feature_enabled("telegram") is False
        assert is_feature_enabled("ldap") is True
        assert is_feature_enabled("slack", default=False) is False


def test_email_sending_disabled_behavior():
    """Verify email sending cleanly skips when Gmail integration is disabled."""
    with patch.dict(os.environ, {"INTEGRATIONS_ENABLED": "false"}):
        ok, msg = send_registration_otp_email("test@example.com", "TestUser", "123456")
        assert ok is False
        assert "disabled in configuration" in msg


def test_google_routes_guard_when_disabled():
    """Verify that accessing Google OAuth routes redirects safely with warning when disabled."""
    client = app.test_client()
    with patch.dict(os.environ, {"INTEGRATIONS_ENABLED": "false"}):
        res_login = client.get("/login/google", follow_redirects=False)
        assert res_login.status_code == 302
        assert res_login.location == "/"

        res_cb = client.get("/callback/google", follow_redirects=False)
        assert res_cb.status_code == 302
        assert res_cb.location == "/"


def test_login_page_google_button_hidden_when_disabled():
    """Verify Google button is not rendered in login HTML when Google OAuth is disabled."""
    client = app.test_client()
    with patch.dict(os.environ, {"INTEGRATIONS_ENABLED": "false"}):
        res = client.get("/")
        assert res.status_code == 200
        assert b"Continue with Google" not in res.data


def test_local_signup_creates_account_directly():
    """Verify that in local mode (email disabled), signup directly creates account without OTP."""
    client = app.test_client()
    with patch.dict(os.environ, {"INTEGRATIONS_ENABLED": "false"}):
        with patch("api.dashboard_app.admin_exists", return_value=True), \
             patch("api.dashboard_app.query_one", return_value=None), \
             patch("api.dashboard_app.register_user", return_value=(True, "User created successfully")) as mock_reg:
            res = client.post("/signup", data={
                "username": "localuser",
                "email": "localuser@test.local",
                "password": "LocalPassword123!"
            }, follow_redirects=False)

            assert res.status_code == 302
            assert res.location == "/"
            mock_reg.assert_called_once_with("localuser", "localuser@test.local", "LocalPassword123!", "user")
