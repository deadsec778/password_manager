from db.connection import get_connection

def purge_deleted_users():
    conn = get_connection()
    cur = conn.cursor()

    sql = "DELETE FROM users WHERE is_deleted = 1"
    cur.execute(sql)
    conn.commit()

    print(f"🧹 Permanently removed {cur.rowcount} deleted users.")

    cur.close()
    conn.close()
