import os
import sys
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from integrations.gmail import (
    OTPManager,
    default_otp_manager,
    render_registration_otp_email,
    render_password_reset_otp_email,
    render_password_changed_email,
    send_registration_otp_email,
    send_password_reset_otp_email,
)
from api.dashboard_app import app, mask_email


def test_email_templates_render():
    """Verify HTML and Text template rendering contains the OTP and username."""
    html_reg, text_reg = render_registration_otp_email("Alice", "123456", 10)
    assert "123456" in html_reg
    assert "Alice" in html_reg
    assert "123456" in text_reg

    html_reset, text_reset = render_password_reset_otp_email("Bob", "654321", 10)
    assert "654321" in html_reset
    assert "Bob" in html_reset
    assert "654321" in text_reset

    html_alert, text_alert = render_password_changed_email("Charlie")
    assert "Charlie" in html_alert


def test_otp_manager_lifecycle():
    """Test OTP creation, failed verification attempt, and successful verification."""
    mgr = OTPManager()
    email = "pytest_user@example.com"
    purpose = "registration"

    # 1. Create OTP
    ok, code, _ = mgr.create_otp(email, purpose, payload={"sample": "data"})
    assert ok is True
    assert len(code) == 6

    # 2. Verify with wrong code -> should fail
    valid_wrong, msg_wrong, _, _ = mgr.verify_otp(email, "000000", purpose)
    assert valid_wrong is False
    assert "Incorrect code" in msg_wrong

    # 3. Verify with correct code -> should succeed
    valid_correct, msg_correct, payload, _ = mgr.verify_otp(email, code, purpose)
    assert valid_correct is True
    assert payload == {"sample": "data"}

    # 4. Verify again -> should fail because already used
    valid_again, msg_again, _, _ = mgr.verify_otp(email, code, purpose)
    assert valid_again is False


def test_mask_email_utility():
    """Test email masking utility."""
    assert mask_email("john.doe@gmail.com") == "j******e@gmail.com"
    assert mask_email("ab@gmail.com") == "a*@gmail.com"
    assert mask_email("invalid") == "invalid"


def test_app_routes_registered():
    """Verify new routes are registered in the Flask application."""
    rules = [rule.rule for rule in app.url_map.iter_rules()]
    assert "/signup" in rules
    assert "/signup/verify" in rules
    assert "/signup/resend" in rules
    assert "/forgot-password" in rules
    assert "/forgot-password/verify" in rules
    assert "/forgot-password/resend" in rules


def test_forgot_password_get_route():
    """Test GET /forgot-password loads without error."""
    client = app.test_client()
    res = client.get("/forgot-password")
    assert res.status_code == 200
    assert b"Forgot Password" in res.data
