import sys
import os
import bcrypt

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from db.connection import get_connection

def update_user_password(user_id, new_master_password):
    """
    Updates the master password hash for the specified user_id.
    Generates a new bcrypt hash and updates the users table.
    """
    conn = get_connection()
    cur = conn.cursor()

    hashed = bcrypt.hashpw(new_master_password.encode(), bcrypt.gensalt()).decode()

    sql = """
    UPDATE users 
    SET master_password_hash = %s 
    WHERE user_id = %s AND is_deleted = 0
    """

    try:
        cur.execute(sql, (hashed, user_id))
        conn.commit()
        cur.close()
        conn.close()
        return True, "Password updated successfully."
    except Exception as e:
        cur.close()
        conn.close()
        return False, str(e)
