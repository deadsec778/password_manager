from db.connection import get_connection
from crypto.crypto_key import get_cipher_for_user

def add_password(vault_id, user_id, role, master_password, service_name, username, plain_password, url=None, notes=None):
    """
    Add a password entry. Uses per-user encryption.
    Admin can add password for ANY user.
    Normal users can add ONLY for themselves.
    """

    conn = get_connection()
    cur = conn.cursor()

    # --- Role enforcement ---
    if role != "admin":
        # user must ONLY use their own user_id
        owner_id = user_id
    else:
        # admin can specify any user_id manually
        owner_id = user_id

    # --- Load cipher (derived from user's master password + stored salt) ---
    cipher = get_cipher_for_user(owner_id, master_password)

    encrypted_pw = cipher.encrypt(plain_password.encode()).decode()

    sql = """
    INSERT INTO passwords (
        vault_id, user_id, service_name, username,
        password_encrypted, url, notes, is_deleted
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
    """

    cur.execute(sql, (
        vault_id,
        owner_id,
        service_name,
        username,
        encrypted_pw,
        url,
        notes
    ))

    conn.commit()

    print(f"🔐 Password for '{service_name}' added successfully.")

    cur.close()
    conn.close()


# --- Test function ---
if __name__ == "__main__":
    # Example: normal user adding their own password
    add_password(
        vault_id=1,
        user_id=1,
        role="user",
        master_password="Sayan@12345",  # needed for encryption
        service_name="Gmail",
        username="sayan@gmail.com",
        plain_password="MyPassword123",
        url="https://mail.google.com",
        notes="My Gmail"
    )
