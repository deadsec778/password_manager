# api/dashboard_app.py
import sys
import os
import uuid
import functools

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
            return render_template("login.html")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not username or not email or not password:
            flash("Please fill all fields.", "warning")
            return render_template("signup.html")
        register_user(username, email, password, role="user")
        flash("Account created! You can now login.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

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

    # make sure admin key exists when needed
    try:
        admin_cipher = get_admin_cipher()
    except FileNotFoundError:
        admin_cipher = None

    if user_cipher is None:
        flash("Encryption context missing. Please login again.", "warning")
        return redirect(url_for("logout"))

    # permission: admin sees all, user only their vault
    # if role != "admin":
    #     v = query_one("SELECT vault_id, vault_name FROM vaults WHERE vault_id = %s AND user_id = %s AND is_deleted = 0", (vault_id, user_id))
    # else:
    #     v = query_one("SELECT vault_id, vault_name FROM vaults WHERE vault_id = %s AND is_deleted = 0", (vault_id,))
    if role != "admin":
     v = query_one("""
        SELECT v.vault_id, v.vault_name, u.username
        FROM vaults v
        JOIN users u ON v.user_id = u.user_id
        WHERE v.vault_id = %s AND v.user_id = %s AND v.is_deleted = 0
     """, (vault_id, user_id))
    else:
     v = query_one("""
        SELECT v.vault_id, v.vault_name, u.username
        FROM vaults v
        JOIN users u ON v.user_id = u.user_id
        WHERE v.vault_id = %s AND v.is_deleted = 0
    """, (vault_id,))


    if not v:
        flash("Vault not found or access denied.", "danger")
        return redirect(url_for("dashboard"))

    # load passwords (join to get owner username)
    if role == "admin":
        rows = query_all("""
            SELECT 
                p.password_id,
                p.user_id,
                u.username AS owner_username,
                p.service_name,
                p.username,
                p.password_user_enc,
                p.password_admin_enc,
                p.url,
                p.notes,
                p.updated_at
            FROM passwords p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.vault_id = %s AND p.is_deleted = 0
        """, (vault_id,))
    else:
        rows = query_all("""
            SELECT 
                p.password_id,
                p.user_id,
                u.username AS owner_username,
                p.service_name,
                p.username,
                p.password_user_enc,
                p.password_admin_enc,
                p.url,
                p.notes,
                p.updated_at
            FROM passwords p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.vault_id = %s AND p.user_id = %s AND p.is_deleted = 0
        """, (vault_id, user_id))

    passwords = []
    for row in rows:
        # unpack exactly as selected above
        (pid, owner_uid, owner_username, service, uname,
         enc_user, enc_admin, url, notes, updated_at) = row

        pw = None
        if role == "admin":
            # admin decrypts with admin cipher (if present)
            if admin_cipher:
                try:
                    pw = admin_cipher.decrypt(enc_admin.encode()).decode()
                except Exception:
                    pw = "🔒 (admin cannot decrypt - corrupted?)"
            else:
                pw = "🔒 (admin key not found)"
        else:
            # normal user decrypts with their own session cipher
            try:
                pw = user_cipher.decrypt(enc_user.encode()).decode()
            except Exception:
                pw = "🔒 (cannot decrypt with your master key)"

        passwords.append({
            "password_id": pid,
            "owner_id": owner_uid,
            "owner_username": owner_username,
            "service": service,
            "username": uname,
            "password": pw,
            "url": url,
            "notes": notes,
            "updated_at": updated_at
        })

    return render_template("vault.html", vault=v, passwords=passwords, role=role)

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
    rows = query_all("SELECT user_id, username, email, role, status FROM users")
    return render_template("admin_users.html", users=rows)

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

# Run dev server
if __name__ == "__main__":
    app.run(debug=True, port=5000)
