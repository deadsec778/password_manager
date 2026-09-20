#list_deleted_vaults.py
from db.connection import get_connection

def list_deleted_vaults(user_id):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    SELECT vault_id, vault_name, description, updated_at
    FROM vaults
    WHERE user_id = %s AND is_deleted = 1
    """

    cur.execute(sql, (user_id,))
    rows = cur.fetchall()

    print("\n🗑️ Deleted Vaults:")
    if not rows:
        print("Trash is empty.")
    else:
        for vault_id, name, desc, updated in rows:
            print(f"ID: {vault_id} | {name} | {desc} | Deleted At: {updated}")

    cur.close()
    conn.close()
