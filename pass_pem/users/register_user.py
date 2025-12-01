import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import bcrypt
from db.connection import get_connection

def register_user(username, email, master_password, role="user"):
    conn = get_connection()
    cur = conn.cursor()

    hashed = bcrypt.hashpw(master_password.encode(), bcrypt.gensalt()).decode()

    sql = """
    INSERT INTO users (username, email, master_password_hash, role, status, is_deleted)
    VALUES (%s, %s, %s, %s, 'active', 0)
    """

    try:
        cur.execute(sql, (username, email, hashed, role))
        conn.commit()
        print(f"👤 User '{username}' registered successfully as {role}.")
    except Exception as e:
        print(f"❌ Failed to register user: {e}")

    cur.close()
    conn.close()
if __name__ == "__main__":
        # Example: create admin user
    register_user(
        username="admin",
        email="admin@example.com",
        master_password="Admin@123",
        role="admin"
    )

    # Example: create normal user
    register_user(
        username="sayan",
        email="sayan@example.com",
        master_password="Sayan@123",
        role="user"
    )
