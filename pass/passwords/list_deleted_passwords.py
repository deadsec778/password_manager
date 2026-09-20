from db.connection import get_connection
from crypto.crypto_key import get_cipher_for_user

def list_deleted_passwords(user_id, role, master_password):
    conn = get_connection()
    cur = conn.cursor()

    # --- ADMIN VIEW: Can see ALL deleted passwords ---
    if role == "admin":
        sql = """
        SELECT 
            password_id,
            user_id,
            vault_id,
            service_name,
            username,
            password_encrypted,
            url,
            notes,
            updated_at
        FROM passwords
        WHERE is_deleted = 1
        """
        cur.execute(sql)

    else:
        # --- USER VIEW: Only their deleted passwords ---
        sql = """
        SELECT 
            password_id,
            user_id,
            vault_id,
            service_name,
            username,
            password_encrypted,
            url,
            notes,
            updated_at
        FROM passwords
        WHERE user_id = %s AND is_deleted = 1
        """
        cur.execute(sql, (user_id,))

    rows = cur.fetchall()

    print("\n🗑️ Deleted Passwords (Trash Bin):")
    print("=" * 60)

    if not rows:
        print("Trash is empty.")
        return

    # --- user-specific decryption cipher ---
    cipher = get_cipher_for_user(user_id, master_password)

    for (
        password_id,
        owner_id,
        vault_id,
        service_name,
        username,
        encrypted_pw,
        url,
        notes,
        updated_at
    ) in rows:

        # decrypt with user's key
        decrypted_pw = cipher.decrypt(encrypted_pw.encode()).decode()

        if role == "admin":
            print(f"""
ID: {password_id}
Owner: {owner_id}
Vault ID: {vault_id}
Service: {service_name}
Username: {username}
Password: {decrypted_pw}
URL: {url}
Notes: {notes}
Deleted At: {updated_at}
------------------------------------------------------------
""")
        else:
            print(f"""
ID: {password_id}
Vault ID: {vault_id}
Service: {service_name}
Username: {username}
Password: {decrypted_pw}
URL: {url}
Notes: {notes}
Deleted At: {updated_at}
------------------------------------------------------------
""")

    cur.close()
    conn.close()


# For Testing
if __name__ == "__main__":
    list_deleted_passwords(
        user_id=1,
        role="user",           # or "admin"
        master_password="Test123"
    )
