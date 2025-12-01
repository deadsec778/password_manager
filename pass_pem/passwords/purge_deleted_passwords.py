from db.connection import get_connection

def purge_deleted_passwords(user_id, role):
    # Only ADMIN can purge deleted passwords
    if role != "admin":
        print("❌ Permission denied: Only admin can purge deleted passwords.")
        return

    conn = get_connection()
    cur = conn.cursor()

    sql = "DELETE FROM passwords WHERE is_deleted = 1"
    cur.execute(sql)
    conn.commit()

    print(f"🧹 Permanently deleted {cur.rowcount} soft-deleted passwords.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    # Example:
    purge_deleted_passwords(
        user_id=1,
        role="admin"   # change to "user" to see restriction
    )
