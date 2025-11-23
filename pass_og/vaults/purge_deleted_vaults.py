#purge_deleted_vaults.py
from db.connection import get_connection

def purge_deleted_vaults():
    conn = get_connection()
    cur = conn.cursor()

    sql = "DELETE FROM vaults WHERE is_deleted = 1"
    cur.execute(sql)
    conn.commit()

    print(f"🧹 Purged {cur.rowcount} deleted vaults.")
    cur.close()
    conn.close()

