import base64
import os
import hashlib
from cryptography.fernet import Fernet
from db.connection import get_connection

# ---------------------------------------------------------------------
# 1. Get or generate salt for a user (stored in database)
# ---------------------------------------------------------------------
def get_or_create_salt(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT salt FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()

    if row and row[0]:
        conn.close()
        # salt is stored as a hex string in the DB; convert back to raw bytes
        try:
            return bytes.fromhex(row[0])
        except Exception:
            # fallback: if somehow a raw bytes string is present, return its bytes
            return row[0].encode()

    # No salt found → create new random salt
    salt = os.urandom(16)

    cur.execute(
        "UPDATE users SET salt = %s WHERE user_id = %s",
        (salt.hex(), user_id)
    )
    conn.commit()

    cur.close()
    conn.close()

    return salt


# ---------------------------------------------------------------------
# 2. Derive encryption key using PBKDF2-HMAC-SHA256
# ---------------------------------------------------------------------
def derive_key(master_password, salt):
    key = hashlib.pbkdf2_hmac(
        'sha256',
        master_password.encode(),
        salt,
        390000  # iterations
    )
    return base64.urlsafe_b64encode(key)


# ---------------------------------------------------------------------
# 3. Return Fernet cipher bound to user's master password
# ---------------------------------------------------------------------
def get_cipher_for_user(user_id, master_password):
    salt = get_or_create_salt(user_id)
    key = derive_key(master_password, salt)
    return Fernet(key)
