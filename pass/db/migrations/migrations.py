import mysql.connector
import os
from getpass import getpass

def run_sql_file(cursor, path):
    with open(path, "r") as f:
        sql = f.read()
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)

def main():
    print("🔐 Enter your MySQL/MariaDB credentials:")
    user = input("Username (default: root): ") or "root"
    password = getpass("Password: ")

    print("\nSelect migration mode:")
    print("1️⃣  Migrate ONLY table structure (001_schema.sql)")
    print("2️⃣  Migrate ONLY initial data (002_initial_data.sql)")
    print("3️⃣  Migrate EVERYTHING (both files)")

    choice = input("\nEnter your choice (1/2/3): ").strip()

    # Validate choice
    if choice not in ["1", "2", "3"]:
        print("❌ Invalid choice. Exiting.")
        return

    print("\nConnecting to database...")

    try:
        conn = mysql.connector.connect(
            host="localhost",
            user=user,
            password=password,
            database="password"
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    cursor = conn.cursor()

    migration_dir = "migrations"

    # Migration logic
    if choice == "1":
        files = ["001_schema.sql"]
    elif choice == "2":
        files = ["002_initial_data.sql"]
    elif choice == "3":
        files = ["001_schema.sql", "002_initial_data.sql"]
    else:
        files = ["001_schema.sql", "002_initial_data.sql", "003_google_oauth.sql"]

    print("\n🚀 Starting migrations...\n")

    for file in files:
        path = os.path.join(migration_dir, file)
        if not os.path.exists(path):
            print(f"⚠️ Skipping missing file: {file}")
            continue

        try:
            print(f"➡️ Running {file} ...")
            run_sql_file(cursor, path)
            conn.commit()
            print(f"✅ Successfully applied: {file}\n")
        except Exception as e:
            print(f"\n❌ ERROR in file: {file}")
            print(f"Error: {e}")
            conn.rollback()
            break

    cursor.close()
    conn.close()

    print("🎉 Migration task completed.")

if __name__ == "__main__":
    main()
