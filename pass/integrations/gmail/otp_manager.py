"""
OTP (One-Time Password) Manager for Email Verification and Password Reset.
Handles cryptographically secure generation, SHA-256 hashing, database storage,
expiration checking, rate-limiting, and verification.
"""

import os
import sys
import json
import secrets
import hashlib
import datetime
import logging
from typing import Optional, Tuple, Dict, Any

# Ensure project root is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from db.connection import get_connection
from .config import (
    OTP_EXPIRY_MINUTES,
    OTP_DIGITS,
    OTP_MAX_ATTEMPTS,
)

logger = logging.getLogger("otp_manager")


def _hash_otp(code: str) -> str:
    """Hash OTP code with SHA-256 for secure DB storage."""
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def ensure_otp_table() -> None:
    """Ensure the email_otps table exists in the database."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS `email_otps` (
      `otp_id` INT(11) NOT NULL AUTO_INCREMENT,
      `email` VARCHAR(150) NOT NULL,
      `user_id` INT(11) DEFAULT NULL,
      `otp_hash` VARCHAR(255) NOT NULL,
      `purpose` ENUM('registration', 'password_reset', 'one_time_login') NOT NULL,
      `payload` TEXT DEFAULT NULL,
      `attempts` INT(11) NOT NULL DEFAULT 0,
      `max_attempts` INT(11) NOT NULL DEFAULT 5,
      `is_used` TINYINT(1) NOT NULL DEFAULT 0,
      `expires_at` DATETIME NOT NULL,
      `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (`otp_id`),
      KEY `idx_email_purpose` (`email`, `purpose`),
      KEY `idx_expires` (`expires_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(create_table_sql)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error ensuring email_otps table: {e}")


class OTPManager:
    """Manages creation, lifecycle, and verification of OTPs."""

    def __init__(self):
        # Auto-ensure table on initialization
        ensure_otp_table()

    def generate_code(self, digits: int = OTP_DIGITS) -> str:
        """Generate a cryptographically secure numeric OTP."""
        max_val = 10 ** digits
        # Secure random integer with leading zeroes
        rand_num = secrets.randbelow(max_val)
        return str(rand_num).zfill(digits)

    def create_otp(
        self,
        email: str,
        purpose: str,  # 'registration', 'password_reset', 'one_time_login'
        user_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        expiry_minutes: int = OTP_EXPIRY_MINUTES,
    ) -> Tuple[bool, str, str]:
        """
        Creates and stores a new OTP for the given email and purpose.
        Invalidates any previous unused OTPs for the same email and purpose.
        Returns: (success, otp_code_or_error, expires_at_str)
        """
        email = email.strip().lower()
        otp_code = self.generate_code()
        otp_hash = _hash_otp(otp_code)
        
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=expiry_minutes)
        payload_json = json.dumps(payload) if payload else None

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Invalidate older active OTPs for the same email and purpose
            cur.execute(
                """
                UPDATE email_otps 
                SET is_used = 1 
                WHERE email = %s AND purpose = %s AND is_used = 0
                """,
                (email, purpose),
            )

            # Insert new OTP record
            cur.execute(
                """
                INSERT INTO email_otps 
                (email, user_id, otp_hash, purpose, payload, attempts, max_attempts, is_used, expires_at)
                VALUES (%s, %s, %s, %s, %s, 0, %s, 0, %s)
                """,
                (email, user_id, otp_hash, purpose, payload_json, OTP_MAX_ATTEMPTS, expires_at),
            )

            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"Generated OTP for {email} (purpose: {purpose}, expires: {expires_at.strftime('%H:%M:%S')})")
            return True, otp_code, expires_at.strftime("%Y-%m-%d %H:%M:%S")

        except Exception as e:
            logger.error(f"Failed to create OTP for {email}: {e}")
            return False, str(e), ""

    def verify_otp(
        self,
        email: str,
        otp_code: str,
        purpose: str,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]], Optional[int]]:
        """
        Verifies the provided OTP for the specified email and purpose.
        Returns: (is_valid, message, payload_dict, user_id)
        """
        email = email.strip().lower()
        code = otp_code.strip()
        
        if not code or len(code) != OTP_DIGITS:
            return False, f"Please enter a valid {OTP_DIGITS}-digit code.", None, None

        now = datetime.datetime.now()

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT otp_id, otp_hash, user_id, payload, attempts, max_attempts, expires_at
                FROM email_otps
                WHERE email = %s AND purpose = %s AND is_used = 0
                ORDER BY otp_id DESC
                LIMIT 1
                """,
                (email, purpose),
            )
            row = cur.fetchone()

            if not row:
                cur.close()
                conn.close()
                return False, "No active verification code found. Please request a new code.", None, None

            otp_id, stored_hash, user_id, payload_str, attempts, max_attempts, expires_at = row

            # Check expiration
            if now > expires_at:
                cur.execute("UPDATE email_otps SET is_used = 1 WHERE otp_id = %s", (otp_id,))
                conn.commit()
                cur.close()
                conn.close()
                return False, "Verification code has expired. Please request a new one.", None, None

            # Check max attempts exceeded
            if attempts >= max_attempts:
                cur.execute("UPDATE email_otps SET is_used = 1 WHERE otp_id = %s", (otp_id,))
                conn.commit()
                cur.close()
                conn.close()
                return False, "Maximum verification attempts exceeded. Please request a new code.", None, None

            # Check code match using constant-time comparison
            input_hash = _hash_otp(code)
            is_match = secrets.compare_digest(input_hash, stored_hash)

            if not is_match:
                # Increment failed attempts
                new_attempts = attempts + 1
                remaining = max(0, max_attempts - new_attempts)
                cur.execute("UPDATE email_otps SET attempts = %s WHERE otp_id = %s", (new_attempts, otp_id))
                conn.commit()
                cur.close()
                conn.close()
                return False, f"Incorrect code. {remaining} attempt(s) remaining.", None, None

            # OTP is valid -> Mark as used
            cur.execute("UPDATE email_otps SET is_used = 1 WHERE otp_id = %s", (otp_id,))
            conn.commit()
            cur.close()
            conn.close()

            payload = json.loads(payload_str) if payload_str else None
            return True, "Code verified successfully.", payload, user_id

        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {e}")
            return False, f"Verification failed due to a database error: {e}", None, None

    def invalidate_otps_for_email(self, email: str, purpose: Optional[str] = None) -> None:
        """Invalidate all active OTPs for a given email."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            if purpose:
                cur.execute("UPDATE email_otps SET is_used = 1 WHERE email = %s AND purpose = %s", (email, purpose))
            else:
                cur.execute("UPDATE email_otps SET is_used = 1 WHERE email = %s", (email,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error invalidating OTPs: {e}")


# Global default manager instance
default_otp_manager = OTPManager()
