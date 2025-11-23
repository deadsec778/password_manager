import mysql.connector

def create_vault(user_id, vault_name, description):
    conn = mysql.connector.connect(
        host="localhost",
        user="pass",
        password="password@321",
        database="password"
    )
    cur = conn.cursor()

    sql = """
    INSERT INTO vaults (user_id, vault_name, description)
    VALUES (%s, %s, %s)
    """
    cur.execute(sql, (user_id, vault_name, description))
    conn.commit()

    print(f"✅ Vault '{vault_name}' created for User ID {user_id}")
    cur.close()
    conn.close()

# Example:
create_vault(1, "Personal", "Private passwords vault")
