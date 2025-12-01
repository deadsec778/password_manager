from db.connection import get_connection

def hard_delete_password(password_id, user_id, role):
    conn = get_connection()
    cur = conn.cursor()

    if role == "admin":
        # Admin can delete ANY password
        sql = "DELETE FROM passwords WHERE password_id = %s"
        cur.execute(sql, (password_id,))
    else:
        # Normal users can delete ONLY their own
        sql = "DELETE FROM passwords WHERE password_id = %s AND user_id = %s"
        cur.execute(sql, (password_id, user_id))

    conn.commit()

    if cur.rowcount > 0:
        print(f"❌ Password entry ID {password_id} permanently deleted.")
    else:
        print(f"⚠️ You don't have permission to delete this password.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    # Example test
    hard_delete_password(
        password_id=6,
        user_id=1,       # who is trying to delete?
        role="user"      # or "admin"
    )
