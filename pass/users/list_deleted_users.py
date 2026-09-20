from db.connection import get_connection

def list_deleted_users():
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    SELECT user_id, username, email, last_login
    FROM users
    WHERE is_deleted = 1
    """

    cur.execute(sql)
    rows = cur.fetchall()

    print("\n🗑️ Deleted Users:")
    if not rows:
        print("Trash is empty.")
    else:
        for uid, uname, email, last_login in rows:
            print(f"ID: {uid} | {uname} | {email} | Last Active: {last_login}")

    cur.close()
    conn.close()
