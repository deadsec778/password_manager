from db.connection import get_connection
from crypto.crypto_key import get_cipher_for_user

def list_deleted_passwords_by_vault(vault_id, user_id, role, master_password):
    conn = get_connection()
    cur = conn.cursor()

    # --- Admin sees ALL deleted passwords in this vault ---
    if role == "admin":
        sql = """
        SELECT 
            password_id,
            user_id,
            service_name,
            username,
            password_encrypted,
            url,
            notes,
            updated_at
        FROM passwords
        WHERE vault_id = %s AND is_deleted = 1
        """
        cur.execute(sql, (vault_id,))

    else:
        # --- Users see ONLY their own deleted passwords ---
        sql = """
        SELECT 
            password_id,
            user_id,
            service_name,
            username,
            password_encrypted,
            url,
            notes,
            updated_at
        FROM passwords
        WHERE vault_id = %s AND user_id = %s AND is_deleted = 1
        """
        cur.execute(sql, (vault_id, user_id))

    rows = cur.fetchall()

    print(f"\n🗑️ Deleted Passwords in Vault {vault_id}:")
    print("=" * 60)

    if not rows:
        print("No deleted passwords in this vault.")
        return

    # Decryption cipher derived from user master password
    cipher = get_cipher_for_user(user_id, master_password)

    for (
        password_id,
        owner_id,
        service_name,
        username,
        encrypted_pw,
        url,
        notes,
        updated_at
    ) in rows:

        # decrypt password securely
        decrypted_pw = cipher.decrypt(encrypted_pw.encode()).decode()

        if role == "admin":
            print(f"""
ID: {password_id}
Owner: {owner_id}
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


# Test Example
if __name__ == "__main__":
    list_deleted_passwords_by_vault(
        vault_id=1,
        user_id=1,
        role="user",            # or "admin"
        master_password="Test123"
    )
