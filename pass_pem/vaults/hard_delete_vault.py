#vaults/hard_delete_vault.py
from db.connection import get_connection

def hard_delete_vault(vault_id):
    conn = get_connection()
    cur = conn.cursor()

    # 1️⃣ Delete passwords belonging to this vault
    sql_passwords = "DELETE FROM passwords WHERE vault_id = %s"
    cur.execute(sql_passwords, (vault_id,))
    deleted_pw_count = cur.rowcount

    # 2️⃣ Delete the vault itself
    sql_vault = "DELETE FROM vaults WHERE vault_id = %s"
    cur.execute(sql_vault, (vault_id,))
    deleted_vault_count = cur.rowcount

    conn.commit()

    if deleted_vault_count > 0:
        print(f"❌ Vault {vault_id} permanently deleted.")
        print(f"🗑️ {deleted_pw_count} associated passwords deleted permanently.")
    else:
        print(f"⚠️ No vault found with ID {vault_id}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    hard_delete_vault(1)

