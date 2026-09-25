import sys
import os
from db.connection import get_connection

def apply_migration():
    sql_path = os.path.join(os.path.dirname(__file__), "003_google_oauth.sql")
    with open(sql_path, "r") as f:
        sql = f.read()

    conn = get_connection()
    cursor = conn.cursor()
    
    print(f"Applying migration: {sql_path}")
    cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()
    print("Migration applied successfully.")

if __name__ == "__main__":
    apply_migration()
