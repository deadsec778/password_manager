"""
Database Migration Runner for Password Manager.
Supports:
1. Fresh setup on a completely blank database (000_full_blank_schema.sql)
2. Seamless upgrade from previous master branch (005_upgrade_from_master.sql)
3. Step-by-step incremental migration (001 -> 002 -> 003 -> 004 -> 005)
4. Programmatic execution via run_all_migrations()
"""

import os
import sys
import mysql.connector
from dotenv import load_dotenv

# Load .env if present
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv(ENV_PATH)

MIGRATIONS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_sql_file(cursor, path):
    """Executes all statements in a SQL file."""
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
        # Split statements by semicolon while ignoring comments
        statements = []
        current_stmt = []
        for line in sql.splitlines():
            clean_line = line.strip()
            if clean_line.startswith("--") or clean_line.startswith("/*"):
                continue
            current_stmt.append(line)
            if clean_line.endswith(";"):
                statements.append("\n".join(current_stmt))
                current_stmt = []
        if current_stmt:
            remaining = "\n".join(current_stmt).strip()
            if remaining:
                statements.append(remaining)

        for statement in statements:
            stmt = statement.strip().rstrip(";")
            if stmt:
                cursor.execute(stmt)


def run_all_migrations(host=None, user=None, password=None, database=None, port=None):
    """Programmatic entry point to run migrations."""
    db_host = host or os.getenv("DB_HOST", "127.0.0.1")
    db_port = int(port or os.getenv("DB_PORT", "3306"))
    db_user = user or os.getenv("DB_USER", "root")
    db_pass = password or os.getenv("DB_PASSWORD", "")
    db_name = database or os.getenv("DB_NAME", "password")

    conn = mysql.connector.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
        database=db_name,
        autocommit=False,
    )
    cursor = conn.cursor()

    files = [
        "000_full_blank_schema.sql",
        "005_upgrade_from_master.sql",
    ]

    applied = []
    for file in files:
        path = os.path.join(MIGRATIONS_DIR, file)
        if os.path.exists(path):
            run_sql_file(cursor, path)
            conn.commit()
            applied.append(file)

    cursor.close()
    conn.close()
    return applied


def main():
    print("==================================================================")
    print("🔐 Password Manager Database Migration Assistant")
    print("==================================================================")

    env_host = os.getenv("DB_HOST", "127.0.0.1")
    env_port = int(os.getenv("DB_PORT", "3306"))
    env_user = os.getenv("DB_USER", "root")
    env_pass = os.getenv("DB_PASSWORD", "")
    env_name = os.getenv("DB_NAME", "password")

    print(f"\nDefault connection from .env: {env_user}@{env_host}:{env_port}/{env_name}")
    use_env = input("Use credentials from .env? (Y/n): ").strip().lower()

    if use_env in ("", "y", "yes"):
        host, port, user, password, database = env_host, env_port, env_user, env_pass, env_name
    else:
        host = input(f"Host (default: {env_host}): ").strip() or env_host
        port_in = input(f"Port (default: {env_port}): ").strip()
        port = int(port_in) if port_in else env_port
        user = input(f"Username (default: {env_user}): ").strip() or env_user
        from getpass import getpass
        password = getpass("Password: ")
        database = input(f"Database name (default: {env_name}): ").strip() or env_name

    print("\nSelect migration mode:")
    print("1️⃣  Fresh Setup / Blank Database (Runs 000_full_blank_schema.sql)")
    print("2️⃣  Upgrade from previous GitHub master branch (Runs 005_upgrade_from_master.sql)")
    print("3️⃣  Full Sequential Suite (001 -> 002 -> 003 -> 004 -> 005)")
    print("4️⃣  Legacy Schema Only (001_schema.sql)")

    choice = input("\nEnter choice (1/2/3/4) [default: 1]: ").strip() or "1"

    if choice == "1":
        files = ["000_full_blank_schema.sql"]
    elif choice == "2":
        files = ["005_upgrade_from_master.sql"]
    elif choice == "3":
        files = [
            "001_schema.sql",
            "002_initial_data.sql",
            "003_google_oauth.sql",
            "004_email_otp.sql",
            "005_upgrade_from_master.sql",
        ]
    elif choice == "4":
        files = ["001_schema.sql"]
    else:
        print("❌ Invalid choice. Exiting.")
        return

    print(f"\nConnecting to {user}@{host}:{port}/{database}...")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            autocommit=False,
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    cursor = conn.cursor()
    print("\n🚀 Applying database migrations...\n")

    for file in files:
        path = os.path.join(MIGRATIONS_DIR, file)
        if not os.path.exists(path):
            print(f"⚠️ Skipping missing file: {file}")
            continue

        try:
            print(f"➡️  Applying {file} ...")
            run_sql_file(cursor, path)
            conn.commit()
            print(f"✅ Successfully applied: {file}\n")
        except Exception as e:
            print(f"\n❌ Error applying {file}: {e}")
            conn.rollback()
            break

    cursor.close()
    conn.close()
    print("🎉 Migration process completed.")


if __name__ == "__main__":
    main()
