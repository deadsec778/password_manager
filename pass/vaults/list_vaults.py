from db.connection import get_connection

def list_vaults(user_id, role):
    conn = get_connection()
    cur = conn.cursor()

    # --- Admin sees all vaults ---
    if role == "admin":
        sql = """
        SELECT vault_id, vault_name, description, user_id
        FROM vaults
        WHERE is_deleted = 0
        """
        cur.execute(sql)
    else:
        # --- Normal users only see their own vaults ---
        sql = """
        SELECT vault_id, vault_name, description, user_id
        FROM vaults
        WHERE user_id = %s AND is_deleted = 0
        """
        cur.execute(sql, (user_id,))

    rows = cur.fetchall()

    print("\n📂 Vaults:")
    print("-" * 50)

    if not rows:
        print("No vaults found.")
    else:
        for vault_id, vault_name, desc, owner_id in rows:
            if role == "admin":
                print(f"ID: {vault_id} | Name: {vault_name} | Owner: {owner_id} | Description: {desc}")
            else:
                print(f"ID: {vault_id} | Name: {vault_name} | Description: {desc}")

    cur.close()
    conn.close()


# Test usage
if __name__ == "__main__":
    # Admin view
    print("ADMIN VIEW:")
    list_vaults(user_id=1, role="admin")

    # Normal user view
    print("\nUSER VIEW:")
    list_vaults(user_id=1, role="user")
