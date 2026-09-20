#restore_vault.py
from db.connection import get_connection

def restore_vault(vault_id):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    UPDATE vaults
    SET is_deleted = 0, updated_at = NOW()
    WHERE vault_id = %s
    """

    cur.execute(sql, (vault_id,))
    conn.commit()

    print(f"♻️ Vault {vault_id} restored.")
    cur.close()
    conn.close()

