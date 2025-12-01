from db.connection import get_connection

def restore_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    UPDATE users
    SET is_deleted = 0, status = 'active'
    WHERE user_id = %s
    """

    cur.execute(sql, (user_id,))
    conn.commit()

    print(f"♻️ Restored user ID {user_id}")

    cur.close()
    conn.close()
