from db.connection import get_connection

def soft_delete_password(password_id, user_id, role):
    conn = get_connection()
    cur = conn.cursor()

    if role == "admin":
        sql = """
        UPDATE passwords
        SET is_deleted = 1, updated_at = NOW()
        WHERE password_id = %s
        """
        cur.execute(sql, (password_id,))
    else:
        sql = """
        UPDATE passwords
        SET is_deleted = 1, updated_at = NOW()
        WHERE password_id = %s AND user_id = %s
        """
        cur.execute(sql, (password_id, user_id))

    conn.commit()

    if cur.rowcount > 0:
        print(f"🗑️ Password entry {password_id} soft-deleted.")
    else:
        print(f"⚠️ You don't have permission to soft-delete this password.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    soft_delete_password(7, user_id=1, role="user")
