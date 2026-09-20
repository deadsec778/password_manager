from db.connection import get_connection

def create_vault(user_id, vault_name, description=None):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
    INSERT INTO vaults (user_id, vault_name, description, is_deleted)
    VALUES (%s, %s, %s, 0)
    """

    cur.execute(sql, (user_id, vault_name, description))
    conn.commit()

    print(f"✅ Vault '{vault_name}' created for User ID {user_id}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    # Example test:
    create_vault(1, "Personal", "Private passwords vault")
