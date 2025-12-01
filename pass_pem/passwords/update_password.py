from db.connection import get_connection
from crypto.crypto_key import get_cipher_for_user

def update_password_entry(password_id, user_id, role, master_password,
                          service_name=None, username=None,
                          new_password=None, url=None, notes=None):

    conn = get_connection()
    cur = conn.cursor()

    # Role-based permission
    if role == "admin":
        owner_check_sql = "SELECT user_id FROM passwords WHERE password_id = %s"
        cur.execute(owner_check_sql, (password_id,))
        row = cur.fetchone()
        if not row:
            print("❌ Password ID does not exist.")
            return
        owner_id = row[0]     # actual owner
    else:
        owner_id = user_id    # normal user can only update own record

    # cipher for encryption (user-specific)
    cipher = get_cipher_for_user(owner_id, master_password)

    fields = []
    values = []

    if service_name:
        fields.append("service_name = %s")
        values.append(service_name)

    if username:
        fields.append("username = %s")
        values.append(username)

    if new_password:
        encrypted = cipher.encrypt(new_password.encode()).decode()
        fields.append("password_encrypted = %s")
        values.append(encrypted)

    if url:
        fields.append("url = %s")
        values.append(url)

    if notes:
        fields.append("notes = %s")
        values.append(notes)

    if not fields:
        print("⚠️ Nothing to update.")
        return

    fields.append("updated_at = NOW()")
    values.append(password_id)

    if role == "admin":
        sql = f"UPDATE passwords SET {', '.join(fields)} WHERE password_id = %s"
        cur.execute(sql, values)
    else:
        sql = f"""
        UPDATE passwords 
        SET {', '.join(fields)} 
        WHERE password_id = %s AND user_id = {owner_id}
        """
        cur.execute(sql, values)

    conn.commit()

    if cur.rowcount > 0:
        print(f"✅ Password ID {password_id} updated successfully.")
    else:
        print("❌ You do not have permission to update this password.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    update_password_entry(
        password_id=1,
        user_id=1,
        role="user",
        master_password="UserMasterPass",
        new_password="NewPass123!",
        notes="Updated from script"
    )
