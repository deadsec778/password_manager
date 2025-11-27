# api/dashboard_app.py
import sys
import os
import uuid
import functools
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except Exception:
    pd = None
    PANDAS_AVAILABLE = False
import csv
from io import TextIOWrapper


from flask import (
    Flask, request, render_template, redirect,
    url_for, flash, session, abort
)
from werkzeug.middleware.proxy_fix import ProxyFix

# ensure project root is importable
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from users.login_user import login_user
from users.register_user import register_user
from db.connection import get_connection
from crypto.crypto_key import get_cipher_for_user
from crypto.admin_cipher import get_admin_cipher  # global admin recovery cipher

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
app.secret_key = os.urandom(32)  # testing only; replace with a safe secret in prod

# In-memory store for per-session cipher objects (testing only)
cipher_store = {}

# -------------------------
# Helpers
# -------------------------
def require_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "sid" not in session or session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def get_cipher_for_session():
    sid = session.get("sid")
    if not sid:
        return None
    return cipher_store.get(sid)

def clear_session_cipher():
    sid = session.get("sid")
    if sid and sid in cipher_store:
        del cipher_store[sid]

# DB convenience
def query_all(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def query_one(sql, params=()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row
def admin_exists():
    row = query_one("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    return row[0] > 0
# -------------------------
# Routes
# -------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        master_password = request.form.get("password", "")
        user_id, role, cipher = login_user(username, master_password)
        if user_id:
            # create server-side session id
            sid = str(uuid.uuid4())
            session["sid"] = sid
            session["user_id"] = user_id
            session["username"] = username
            session["role"] = role
            # store cipher temporarily in memory
            cipher_store[sid] = cipher
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Login failed. Check username/password.", "danger")
            return render_template("login.html", admin_exists=admin_exists())

    return render_template("login.html", admin_exists=admin_exists())

@app.route("/signup", methods=["GET", "POST"])
def signup():
    # check if admin already exists
    is_first_admin = not admin_exists()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Please fill all fields.", "warning")
            return render_template("signup.html", is_first_admin=is_first_admin)

        # if no admin exists, first signup becomes admin
        if is_first_admin:
            role = "admin"
        else:
            role = "user"

        register_user(username, email, password, role)
        flash(f"Account created successfully!", "success")
        return redirect(url_for("login"))

    return render_template("signup.html", is_first_admin=is_first_admin)


@app.route("/logout")
@require_login
def logout():
    clear_session_cipher()
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

# @app.route("/dashboard")
# @require_login
# def dashboard():
    # user_id = session["user_id"]
    # role = session["role"]
# 
    # if role == "admin":
        # vaults = query_all("SELECT vault_id, vault_name, description, user_id FROM vaults WHERE is_deleted = 0")
    # else:
        # vaults = query_all("SELECT vault_id, vault_name, description, user_id FROM vaults WHERE user_id = %s AND is_deleted = 0", (user_id,))
# 
    # return render_template("dashboard.html", vaults=vaults, role=role)

@app.route("/dashboard")
@require_login
def dashboard():
    user_id = session["user_id"]
    role = session["role"]

    if role == "admin":
        vaults = query_all("""
            SELECT 
                v.vault_id,
                v.vault_name,
                v.description,
                u.username   AS owner_username
            FROM vaults v
            JOIN users u ON v.user_id = u.user_id
            WHERE v.is_deleted = 0
        """)
    else:
        vaults = query_all("""
            SELECT 
                v.vault_id,
                v.vault_name,
                v.description,
                u.username   AS owner_username
            FROM vaults v
            JOIN users u ON v.user_id = u.user_id
            WHERE v.user_id = %s AND v.is_deleted = 0
        """, (user_id,))

    return render_template("dashboard.html", vaults=vaults, role=role)


# View vault and its passwords
@app.route("/vaults/<int:vault_id>")
@require_login
def view_vault(vault_id):
    user_id = session["user_id"]
    role = session["role"]
    user_cipher = get_cipher_for_session()
    admin_cipher = None

    try:
        admin_cipher = get_admin_cipher()
        print(f"DEBUG: Admin cipher loaded successfully")
    except Exception as e:
        print(f"DEBUG: Admin cipher error: {e}")
        pass

    q = request.args.get("q", "").strip().lower()

    # permission check
    if role == "admin":
        base_sql = """
            SELECT p.password_id, p.user_id, u.username,
                   p.service_name, p.username,
                   p.password_user_enc, p.password_admin_enc,
                   p.url, p.notes, p.updated_at
            FROM passwords p 
            JOIN users u ON p.user_id = u.user_id
            WHERE p.vault_id = %s AND p.is_deleted = 0
        """
        params = (vault_id,)
    else:
        base_sql = """
            SELECT p.password_id, p.user_id, u.username, 
                   p.service_name, p.username,
                   p.password_user_enc, p.password_admin_enc,
                   p.url, p.notes, p.updated_at
            FROM passwords p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.vault_id = %s AND p.user_id = %s AND p.is_deleted = 0
        """
        params = (vault_id, user_id)

    rows = query_all(base_sql, params)
    print(f"DEBUG: Found {len(rows)} passwords in vault {vault_id}")

    # If search is used → filter in python (fast enough)
    if q:
        rows = [
            r for r in rows
            if q in r[2].lower()      # owner username
            or q in r[3].lower()      # service
            or q in r[4].lower()      # username
            or (r[7] and q in r[7].lower())  # url
            or (r[8] and q in r[8].lower())  # notes
        ]

    # decrypt after filtering
    passwords = []
    for row in rows:
        pid, owner_uid, owner_username, service, uname, enc_user, enc_admin, url, notes, updated_at = row
        
        print(f"DEBUG: Processing password ID {pid}, owner: {owner_username} (ID: {owner_uid})")
        print(f"DEBUG - Admin cipher available: {admin_cipher is not None}")
        print(f"DEBUG - enc_admin exists: {enc_admin is not None}")
        print(f"DEBUG - enc_user exists: {enc_user is not None}")

        if role == "admin" and admin_cipher:
            try:
                print(f"DEBUG: Attempting admin decryption for password {pid}")
                pw = admin_cipher.decrypt(enc_admin.encode()).decode()
                print(f"DEBUG: Admin decryption SUCCESS for password {pid}")
            except Exception as e:
                print(f"DEBUG: Admin decryption FAILED for password {pid}: {e}")
                pw = "🔒"
        else:
            try:
                print(f"DEBUG: Attempting user decryption for password {pid}")
                pw = user_cipher.decrypt(enc_user.encode()).decode()
                print(f"DEBUG: User decryption SUCCESS for password {pid}")
            except Exception as e:
                print(f"DEBUG: User decryption FAILED for password {pid}: {e}")
                pw = "🔒"

        passwords.append({
            "password_id": pid,
            "owner_username": owner_username,
            "service": service,
            "username": uname,
            "password": pw,
            "url": url,
            "notes": notes,
            "updated_at": updated_at
        })

    # ... rest of your pagination code ...


    # --- Pagination ---
    page = int(request.args.get("page", 1))
    per_page = 20  # you can make it 10, 25, 50, etc.
    start = (page - 1) * per_page
    end = start + per_page

    paged_passwords = passwords[start:end]

    total_pages = (len(passwords) + per_page - 1) // per_page

    return render_template(
    "vault.html",
    vault=(vault_id,"Vault"),
    passwords=paged_passwords,
    page=page,
    total_pages=total_pages,
    role=role
)

# Add vault
@app.route("/vaults/add", methods=["GET", "POST"])
@require_login
def add_vault():
    if request.method == "POST":
        name = request.form.get("vault_name", "").strip()
        desc = request.form.get("description", "").strip()
        user_id = session["user_id"]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO vaults (user_id, vault_name, description, is_deleted) VALUES (%s,%s,%s,0)", (user_id, name, desc))
        conn.commit()
        cur.close()
        conn.close()
        flash("Vault created.", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_vault.html")

# Add password (ENVELOPE: store both user & admin ciphertexts)
@app.route("/vaults/<int:vault_id>/add_password", methods=["GET","POST"])
@require_login
def add_password(vault_id):
    user_id = session["user_id"]
    user_cipher = get_cipher_for_session()

    try:
        admin_cipher = get_admin_cipher()
    except FileNotFoundError:
        admin_cipher = None

    if user_cipher is None:
        flash("Encryption context missing. Please login again.", "warning")
        return redirect(url_for("logout"))

    if request.method == "POST":
        service = request.form.get("service_name", "").strip()
        username_field = request.form.get("username", "").strip()
        plain_pw = request.form.get("password", "")
        url_field = request.form.get("url", "").strip()
        notes_field = request.form.get("notes", "").strip()

        owner_id = user_id  # owner = logged in user

        # Encrypt for both user & admin (if admin key exists)
        encrypted_for_user = user_cipher.encrypt(plain_pw.encode()).decode()

        if admin_cipher:
            encrypted_for_admin = admin_cipher.encrypt(plain_pw.encode()).decode()
        else:
            # create a placeholder NULL value if admin key missing
            encrypted_for_admin = None

        conn = get_connection()
        cur = conn.cursor()

        sql = """
            INSERT INTO passwords 
            (vault_id, user_id, service_name, username,
             password_user_enc, password_admin_enc,
             url, notes, is_deleted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            vault_id,
            owner_id,
            service,
            username_field,
            encrypted_for_user,
            encrypted_for_admin,
            url_field,
            notes_field,
            0
        )

        cur.execute(sql, values)
        conn.commit()
        cur.close()
        conn.close()

        flash("Password saved successfully!", "success")
        return redirect(url_for("view_vault", vault_id=vault_id))

    return render_template("add_password.html", vault_id=vault_id)


# Soft delete password
@app.route("/passwords/<int:password_id>/soft_delete", methods=["POST"])
@require_login
def soft_delete_password_route(password_id):
    user_id = session["user_id"]
    role = session["role"]
    conn = get_connection()
    cur = conn.cursor()
    if role == "admin":
        cur.execute("UPDATE passwords SET is_deleted = 1, updated_at = NOW() WHERE password_id = %s", (password_id,))
    else:
        cur.execute("UPDATE passwords SET is_deleted = 1, updated_at = NOW() WHERE password_id = %s AND user_id = %s", (password_id, user_id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Password moved to trash (if permitted).", "info")
    return redirect(request.referrer or url_for("dashboard"))

# Trash listing
@app.route("/trash")
@require_login
def trash():
    user_id = session["user_id"]
    role = session["role"]
    user_cipher = get_cipher_for_session()

    try:
        admin_cipher = get_admin_cipher()
    except FileNotFoundError:
        admin_cipher = None

    if role == "admin":
        rows = query_all("""
            SELECT p.password_id, p.user_id, u.username, p.service_name, p.username, p.password_user_enc, p.password_admin_enc, p.updated_at
            FROM passwords p JOIN users u ON p.user_id = u.user_id
            WHERE p.is_deleted = 1
        """)
    else:
        rows = query_all("""
            SELECT p.password_id, p.user_id, u.username, p.service_name, p.username, p.password_user_enc, p.password_admin_enc, p.updated_at
            FROM passwords p JOIN users u ON p.user_id = u.user_id
            WHERE p.is_deleted = 1 AND p.user_id = %s
        """, (user_id,))

    items = []
    for pid, owner_uid, owner_username, service, uname, enc_user, enc_admin, updated_at in rows:
        if role == "admin":
            if admin_cipher:
                try:
                    pw = admin_cipher.decrypt(enc_admin.encode()).decode()
                except Exception:
                    pw = "🔒 (admin cannot decrypt)"
            else:
                pw = "🔒 (admin key missing)"
        else:
            try:
                pw = user_cipher.decrypt(enc_user.encode()).decode()
            except Exception:
                pw = "🔒 (cannot decrypt with your key)"
        items.append({"id": pid, "owner": owner_username, "service": service, "username": uname, "password": pw, "updated_at": updated_at})

    return render_template("trash.html", items=items, role=role)

# Admin area - list users
@app.route("/admin/users")
@require_login
def admin_users():
    if session.get("role") != "admin":
        abort(403)

    q = request.args.get("q", "").strip().lower()

    rows = query_all("SELECT user_id, username, email, role, status FROM users")

    if q:
        rows = [
            r for r in rows
            if q in r[1].lower() or q in r[2].lower() or q in r[3].lower()
        ]

    return render_template("admin_users.html", users=rows, q=q)


@app.route("/admin/import_passwords")
@require_login
def import_passwords_page():
    # Admin-only landing page to pick a vault to import into
    if session.get("role") != "admin":
        abort(403)

    # List all vaults with owner info
    rows = query_all("""
        SELECT v.vault_id, v.vault_name, v.description, u.username
        FROM vaults v JOIN users u ON v.user_id = u.user_id
        WHERE v.is_deleted = 0
    """)

    # rows: list of tuples (vault_id, vault_name, description, owner_username)
    return render_template("import_passwords.html", vaults=rows)



#add user route only for  the admins
@app.route("/admin/add_user", methods=["GET", "POST"])
@require_login
def admin_add_user():
    if session.get("role") != "admin":
        abort(403)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "user")

        if not username or not email or not password:
            flash("All fields are required.", "warning")
            return redirect(url_for("admin_add_user"))

        # use your existing register logic
        register_user(username, email, password, role)

        flash("User created successfully!", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_add_user.html")


# Simple restore route for password (admin or owner)
@app.route("/passwords/<int:password_id>/restore", methods=["POST"])
@require_login
def restore_password_route(password_id):
    user_id = session["user_id"]
    role = session["role"]
    conn = get_connection()
    cur = conn.cursor()
    if role == "admin":
        cur.execute("UPDATE passwords SET is_deleted = 0, updated_at = NOW() WHERE password_id = %s", (password_id,))
    else:
        cur.execute("UPDATE passwords SET is_deleted = 0, updated_at = NOW() WHERE password_id = %s AND user_id = %s", (password_id, user_id))
    conn.commit()
    changed = cur.rowcount
    cur.close()
    conn.close()
    if changed > 0:
        flash("Password restored successfully.", "success")
    else:
        flash("You cannot restore this password.", "danger")
    return redirect(request.referrer or url_for("trash"))

#import password with the csv file
@app.route("/vaults/<int:vault_id>/import", methods=["GET"])
@require_login
def import_password_mapping_page(vault_id):
    if session.get("role") != "admin":
        abort(403)

    # Admin selects a file first
    return render_template("password_import.html", vault_id=vault_id)
#iport password with the csv file - step 2
@app.route("/vaults/<int:vault_id>/import_preview", methods=["POST"])
@require_login
def import_preview(vault_id):
    if session.get("role") != "admin":
        abort(403)

    uploaded = request.files.get("file")
    if not uploaded:
        flash("Upload a CSV or Excel file.", "danger")
        return redirect(url_for("import_password_mapping_page", vault_id=vault_id))

    filename = uploaded.filename.lower()

    # CSV
    if filename.endswith(".csv"):
        text = TextIOWrapper(uploaded.stream, encoding="utf-8")
        reader = csv.DictReader(text)
        rows = list(reader)
        header = list(reader.fieldnames)

    # Excel
    elif filename.endswith(".xlsx"):
        if not PANDAS_AVAILABLE:
            flash("Install pandas for XLSX import.", "danger")
            return redirect(url_for("import_password_mapping_page", vault_id=vault_id))
        uploaded.stream.seek(0)
        df = pd.read_excel(uploaded.stream)
        rows = df.to_dict(orient="records")
        header = list(df.columns)

    else:
        flash("Only .csv or .xlsx files allowed.", "danger")
        return redirect(url_for("import_password_mapping_page", vault_id=vault_id))

    # Coerce header and row keys/values to plain Python types (strings) so session
    # JSON serialization doesn't fail when keys are ints or values are numpy types.
    safe_header = [str(h) for h in header]

    safe_rows = []
    for r in rows:
        safe_r = {}
        # r may be a dict-like (from csv.DictReader or pandas)
        for k, v in r.items():
            # convert keys and values to strings, map None to empty string
            sk = str(k)
            if v is None:
                sv = ""
            else:
                sv = str(v)
            safe_r[sk] = sv
        safe_rows.append(safe_r)

    session["import_rows"] = safe_rows
    session["import_header"] = safe_header

    return render_template(
        "import_mapping.html",
        vault_id=vault_id,
        header=header
    )

# Final import step to the DB
@app.route("/vaults/<int:vault_id>/import_apply", methods=["POST"])
@require_login
def import_apply(vault_id):
    if session.get("role") != "admin":
        abort(403)

    rows = session.get("import_rows")
    header = session.get("import_header")

    if not rows:
        flash("Import session expired. Please upload again.", "danger")
        return redirect(url_for("import_password_mapping_page", vault_id=vault_id))

    # Column mappings
    map_service = request.form.get("map_service")
    map_username = request.form.get("map_username")
    map_password = request.form.get("map_password")
    map_url = request.form.get("map_url")
    map_notes = request.form.get("map_notes")

    if not map_service or not map_username or not map_password:
        flash("Service, Username and Password mappings are required.", "danger")
        return redirect(url_for("import_password_mapping_page", vault_id=vault_id))

    # Load admin cipher
    try:
        admin_cipher = get_admin_cipher()
        print(f"IMPORT DEBUG: Admin cipher loaded successfully")
    except Exception as e:
        print(f"IMPORT DEBUG: Admin cipher error: {e}")
        flash("Admin key missing.", "danger")
        return redirect(url_for("import_password_mapping_page", vault_id=vault_id))

    # Get the vault owner
    vault_info = query_one("SELECT user_id, vault_name FROM vaults WHERE vault_id = %s", (vault_id,))
    if not vault_info:
        flash("Vault not found.", "danger")
        return redirect(url_for("dashboard"))
    
    vault_owner_id = vault_info[0]
    vault_name = vault_info[1]
    print(f"IMPORT DEBUG: Importing to vault '{vault_name}' owned by user ID {vault_owner_id}")
    
    # Get cipher for the vault owner
    try:
        vault_owner_cipher = get_cipher_for_user(vault_owner_id)
        print(f"IMPORT DEBUG: Vault owner cipher loaded successfully")
    except Exception as e:
        print(f"IMPORT DEBUG: Vault owner cipher error: {e}")
        vault_owner_cipher = None

    conn = get_connection()
    cur = conn.cursor()

    count_ok = 0
    count_fail = 0

    for i, r in enumerate(rows):
        try:
            service = str(r.get(map_service, "")).strip()
            uname = str(r.get(map_username, "")).strip()
            plain = str(r.get(map_password, "")).strip()
            url = str(r.get(map_url, "")).strip() if map_url else ""
            notes = str(r.get(map_notes, "")).strip() if map_notes else ""

            print(f"IMPORT DEBUG: Processing row {i+1}, service: {service}, username: {uname}")

            # Encrypt for admin (recovery) - this is crucial for admin viewing
            enc_admin = admin_cipher.encrypt(plain.encode()).decode()
            print(f"IMPORT DEBUG: Admin encryption successful")

            # Encrypt for vault owner
            enc_user = None
            if vault_owner_cipher:
                try:
                    enc_user = vault_owner_cipher.encrypt(plain.encode()).decode()
                    print(f"IMPORT DEBUG: User encryption successful")
                except Exception as e:
                    print(f"IMPORT DEBUG: User encryption failed: {e}")
                    enc_user = None
            else:
                print(f"IMPORT DEBUG: No vault owner cipher available")

            cur.execute("""
                INSERT INTO passwords
                (vault_id, user_id, service_name, username,
                 password_user_enc, password_admin_enc,
                 url, notes, is_deleted)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,0)
            """, (
                vault_id,
                vault_owner_id,  # Use vault owner's ID
                service,
                uname,
                enc_user,
                enc_admin,
                url,
                notes
            ))

            count_ok += 1
            print(f"IMPORT DEBUG: Row {i+1} imported successfully")

        except Exception as e:
            print(f"IMPORT DEBUG: Row {i+1} import failed: {e}")
            count_fail += 1

    conn.commit()
    cur.close()
    conn.close()

    flash(f"Import finished. Success: {count_ok}, Failed: {count_fail}", "success")
    return redirect(url_for("view_vault", vault_id=vault_id))

# Run dev server
if __name__ == "__main__":
    app.run(debug=True, port=5000)
