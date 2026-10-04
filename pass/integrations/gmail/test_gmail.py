"""
CLI test utility for Gmail integration.
Allows testing email delivery, SMTP credentials, and OTP flows directly from the command line.

Usage:
  python test_gmail.py --email recipient@example.com --type test
  python test_gmail.py --email recipient@example.com --type registration --username johndoe
  python test_gmail.py --email recipient@example.com --type reset --username johndoe
"""

import sys
import os
import argparse

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from integrations.gmail import (
    is_gmail_configured,
    GMAIL_SENDER_EMAIL,
    GMAIL_SMTP_HOST,
    GMAIL_SMTP_PORT,
    send_registration_otp_email,
    send_password_reset_otp_email,
    default_sender,
    default_otp_manager,
)


def main():
    parser = argparse.ArgumentParser(description="Test Gmail Integration for Password Manager")
    parser.add_argument("--email", required=True, help="Recipient email address")
    parser.add_argument("--type", choices=["test", "registration", "reset"], default="test", help="Type of email to send")
    parser.add_argument("--username", default="TestUser", help="Username for template rendering")
    parser.add_argument("--code", default=None, help="Custom OTP code (optional)")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print(" [EMAIL SERVICE] GMAIL INTEGRATION DIAGNOSTICS & TEST UTILITY")
    print("=" * 60)
    print(f"  Sender Email  : {GMAIL_SENDER_EMAIL or '[NOT CONFIGURED - Set in .env]'}")
    print(f"  SMTP Host     : {GMAIL_SMTP_HOST}:{GMAIL_SMTP_PORT}")
    print(f"  Configured    : {'[YES - LIVE SMTP]' if is_gmail_configured() else '[NO - SIMULATION / LOG MODE]'}")
    print(f"  Recipient     : {args.email}")
    print(f"  Action        : {args.type.upper()}")
    print("=" * 60 + "\n")

    code = args.code or default_otp_manager.generate_code()

    if args.type == "test":
        subject = "Gmail SMTP Connection Test - DeadSec Password Manager"
        html = f"""
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #2563eb; border-radius: 10px;">
          <h2 style="color: #2563eb;">Gmail SMTP Connection Successful! 🎉</h2>
          <p>This is a test email confirming that your Gmail App Password and SMTP integration are working properly.</p>
          <p><strong>Sender:</strong> {GMAIL_SENDER_EMAIL}</p>
          <p><strong>Timestamp:</strong> {os.getenv('APP_NAME', 'Password Manager')}</p>
        </div>
        """
        success, msg = default_sender.send_email(args.email, subject, html, "Gmail SMTP Connection Test Successful!")

    elif args.type == "registration":
        print(f"Generating and sending Registration OTP: {code}")
        success, msg = send_registration_otp_email(args.email, args.username, code)

    elif args.type == "reset":
        print(f"Generating and sending Password Reset OTP: {code}")
        success, msg = send_password_reset_otp_email(args.email, args.username, code)

    if success:
        print(f"\n[+] Result: SUCCESS")
        print(f"    Message: {msg}\n")
    else:
        print(f"\n[-] Result: FAILED")
        print(f"    Error: {msg}\n")


if __name__ == "__main__":
    main()
