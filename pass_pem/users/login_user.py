import bcrypt
from db.connection import get_connection
from crypto.crypto_key import get_cipher_for_user

def login_user(username, master_password):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    SELECT user_id, master_password_hash, role
    FROM users
    WHERE username = %s AND is_deleted = 0 AND status = 'active'
    """

    cur.execute(sql, (username,))
    row = cur.fetchone()

    if not row:
        print("❌ Invalid username or user is disabled/deleted.")
        return None, None, None

    user_id, stored_hash, role = row

    # Verify bcrypt password
    if not bcrypt.checkpw(master_password.encode(), stored_hash.encode()):
        print("❌ Incorrect password.")
        cur.close()
        conn.close()
        return None, None, None

    # Update last_login timestamp
    update_sql = "UPDATE users SET last_login = NOW() WHERE user_id = %s"
    cur.execute(update_sql, (user_id,))
    conn.commit()

    cur.close()
    conn.close()

    # --- NEW: derive Fernet cipher using user master password ---
    cipher = get_cipher_for_user(user_id, master_password)

    print(f"✅ Login successful for '{username}' — role: {role}")

    # Return everything needed by CLI/API
    return user_id, role, cipher


if __name__ == "__main__":
    uid, role, cipher = login_user("sayan", "Master123")
    print("Returned:", uid, role, cipher)
