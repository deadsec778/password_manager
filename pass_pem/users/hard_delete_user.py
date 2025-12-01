from db.connection import get_connection

def hard_delete_user(user_id):
    conn = get_connection()
    cur = conn.cursor()

    sql = "DELETE FROM users WHERE user_id = %s"
    cur.execute(sql, (user_id,))
    conn.commit()

    print(f"❌ User ID {user_id} permanently deleted.")

    cur.close()
    conn.close()

