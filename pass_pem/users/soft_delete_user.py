from db.connection import get_connection

def soft_delete_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    UPDATE users
    SET is_deleted = 1, status = 'disabled', last_login = NOW()
    WHERE user_id = %s
    """

    cur.execute(sql, (user_id,))
    conn.commit()

    print(f"🗑️ User ID {user_id} soft-deleted.")

    cur.close()
    conn.close()
