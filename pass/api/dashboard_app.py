# api/dashboard_app.py
import sys
import os
import uuid
import functools
import json
import datetime
import secrets
import requests
from dotenv import load_dotenv

# Load .env from the pass/ root (one level above api/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
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
    url_for, flash, session, abort, send_from_directory
)
from werkzeug.middleware.proxy_fix import ProxyFix

# ensure project root is importable
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from users.login_user import login_user
from users.register_user import register_user
from users.update_user_password import update_user_password
from db.connection import get_connection
from crypto.crypto_key import get_cipher_for_user
from crypto.admin_cipher import get_admin_cipher
from integrations import (
    is_integrations_master_enabled,
    is_google_oauth_enabled,
    is_gmail_enabled,
    is_feature_enabled,
    get_integrations_status,
)
from integrations.gmail import (
    send_registration_otp_email,
    send_password_reset_otp_email,
    send_password_changed_notification,
    default_otp_manager,
    is_gmail_configured,
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
# Use FLASK_SECRET_KEY from .env; fallback to urandom so dev isn't strictly broken on missing .env
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32))

@app.context_processor
def inject_integrations_context():
    return {
        "integrations_enabled": is_integrations_master_enabled(),
        "google_oauth_enabled": is_google_oauth_enabled(),
        "gmail_integration_enabled": is_gmail_enabled(),
        "integrations_status": get_integrations_status(),
    }

# Redis settings placeholder
REDIS_ACTIVE = os.getenv("REDIS_ACTIVE", "false").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

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

def decrypt_password_for_view(role, admin_cipher, user_cipher, enc_admin, enc_user, owner_uid, pid, session_user_id):
    if role == "admin" and admin_cipher:
        try:
            return admin_cipher.decrypt(enc_admin.encode()).decode()
        except Exception:
            return "🔒"
    else:
        pw = None
        if enc_user:
            try:
                pw = user_cipher.decrypt(enc_user.encode()).decode()
            except Exception:
                pw = None
        
        # Migration fallback
        if (not pw) and enc_admin and (owner_uid == session_user_id) and admin_cipher:
            try:
                recovered = admin_cipher.decrypt(enc_admin.encode()).decode()
                reenc = user_cipher.encrypt(recovered.encode()).decode()
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE passwords SET password_user_enc = %s WHERE password_id = %s", (reenc, pid))
                conn.commit()
                cur.close()
                conn.close()
                pw = recovered
            except Exception:
                pw = None
                
        if not pw:
            pw = "🔒"
        return pw

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
    return bool(row and row[0] > 0)
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
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Please fill all fields.", "warning")
            return render_template("signup.html", is_first_admin=is_first_admin)

        # Check for existing username or email before sending OTP
        existing_user = query_one("SELECT user_id FROM users WHERE username = %s AND is_deleted = 0", (username,))
        if existing_user:
            flash(f"Username '{username}' is already taken. Please choose another.", "danger")
            return render_template("signup.html", is_first_admin=is_first_admin, username=username, email=email)

        existing_email = query_one("SELECT user_id FROM users WHERE email = %s AND is_deleted = 0", (email,))
        if existing_email:
            flash(f"Email '{email}' is already registered. Please log in or reset your password.", "danger")
            return render_template("signup.html", is_first_admin=is_first_admin, username=username, email=email)

        # if no admin exists, first signup becomes admin
        role = "admin" if is_first_admin else "user"

        # Local Mode: If Gmail integration is disabled, create account immediately without OTP
        if not is_gmail_enabled():
            success, reg_msg = register_user(username, email, password, role)
            if not success:
                flash(f"Could not create account: {reg_msg}", "danger")
                return render_template("signup.html", is_first_admin=is_first_admin, username=username, email=email)
            flash("Account created successfully (Local Mode)! You can now log in.", "success")
            return redirect(url_for("login"))

        payload = {
            "username": username,
            "email": email,
            "password": password,
            "role": role,
        }

        # Generate registration OTP
        ok, otp_code, _ = default_otp_manager.create_otp(
            email=email,
            purpose="registration",
            payload=payload
        )

        if not ok:
            flash(f"Could not initiate registration: {otp_code}", "danger")
            return render_template("signup.html", is_first_admin=is_first_admin, username=username, email=email)

        # Send email via Gmail integration
        send_ok, send_msg = send_registration_otp_email(to_email=email, username=username, otp_code=otp_code)

        # Save pending signup in session
        session["pending_signup_email"] = email
        session["pending_signup_username"] = username
        session["pending_signup_payload"] = payload

        if send_ok:
            flash(f"A 6-digit verification code has been sent to {email}. Please enter it below to activate your account.", "info")
        else:
            flash(f"Failed to send email to {email}: {send_msg}", "danger")

        return redirect(url_for("verify_signup_otp"))

    return render_template("signup.html", is_first_admin=is_first_admin)


@app.route("/signup/verify", methods=["GET", "POST"])
def verify_signup_otp():
    if not is_gmail_enabled():
        flash("Email verification is disabled in local mode.", "info")
        return redirect(url_for("login"))

    email = session.get("pending_signup_email")
    if not email:
        flash("No pending registration found. Please fill out the registration form.", "warning")
        return redirect(url_for("signup"))

    if request.method == "POST":
        otp_code = request.form.get("otp_code", "").strip()
        is_valid, msg, payload, _ = default_otp_manager.verify_otp(email, otp_code, purpose="registration")

        if not is_valid:
            flash(msg, "danger")
            return render_template("signup_verify.html", email=email)

        # Retrieve user details from payload or session
        reg_data = payload or session.get("pending_signup_payload", {})
        username = reg_data.get("username")
        user_email = reg_data.get("email") or email
        password = reg_data.get("password")
        role = reg_data.get("role", "user")

        if not username or not password:
            flash("Registration session data missing. Please try signing up again.", "danger")
            return redirect(url_for("signup"))

        success, reg_msg = register_user(username, user_email, password, role)
        if not success:
            flash(f"Could not create account: {reg_msg}", "danger")
            return redirect(url_for("signup"))

        # Clear pending signup session keys
        session.pop("pending_signup_email", None)
        session.pop("pending_signup_username", None)
        session.pop("pending_signup_payload", None)

        flash("🎉 Account verified and created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup_verify.html", email=email)


@app.route("/signup/resend", methods=["POST"])
def resend_signup_otp():
    if not is_gmail_enabled():
        flash("Email service is disabled in local mode.", "warning")
        return redirect(url_for("login"))

    email = session.get("pending_signup_email")
    username = session.get("pending_signup_username", "User")
    payload = session.get("pending_signup_payload")

    if not email:
        flash("No active signup session. Please start registration.", "warning")
        return redirect(url_for("signup"))

    ok, otp_code, _ = default_otp_manager.create_otp(
        email=email,
        purpose="registration",
        payload=payload
    )

    if ok:
        send_ok, send_msg = send_registration_otp_email(to_email=email, username=username, otp_code=otp_code)
        if send_ok:
            flash(f"A new verification code has been sent to {email}.", "info")
        else:
            flash(f"Failed to send email: {send_msg}", "danger")
    else:
        flash("Failed to generate a new verification code. Please try again.", "danger")

    return redirect(url_for("verify_signup_otp"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if not is_gmail_enabled():
        if request.method == "POST":
            flash("Email integration is disabled in local mode. Please contact your system administrator to reset credentials.", "warning")
            return render_template("forgot_password.html", identity=request.form.get("identity", ""))
        return render_template("forgot_password.html")

    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        if not identity:
            flash("Please enter your username or email address.", "warning")
            return render_template("forgot_password.html", identity=identity)

        user = query_one(
            """
            SELECT user_id, username, email, role, status 
            FROM users 
            WHERE (username = %s OR email = %s) AND is_deleted = 0
            """,
            (identity, identity)
        )

        if not user:
            flash("No active account found matching that username or email.", "danger")
            return render_template("forgot_password.html", identity=identity)

        user_id, username, email, role, status = user

        if status == "disabled":
            flash("This account has been disabled. Please contact your administrator.", "danger")
            return render_template("forgot_password.html", identity=identity)

        payload = {"user_id": user_id, "username": username, "email": email, "role": role}
        ok, otp_code, _ = default_otp_manager.create_otp(
            email=email,
            purpose="password_reset",
            user_id=user_id,
            payload=payload
        )

        if not ok:
            flash("Could not generate security code. Please try again.", "danger")
            return render_template("forgot_password.html", identity=identity)

        # Send password reset / one-time login OTP
        send_ok, send_msg = send_password_reset_otp_email(to_email=email, username=username, otp_code=otp_code)

        session["reset_email"] = email
        session["reset_user_id"] = user_id
        session["reset_username"] = username
        session["reset_role"] = role

        if send_ok:
            flash(f"A one-time security code has been sent to your registered email ({mask_email(email)}).", "info")
        else:
            flash(f"Failed to send email: {send_msg}", "danger")

        return redirect(url_for("verify_forgot_password_otp"))

    return render_template("forgot_password.html")


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email
    user_part, domain_part = email.split("@", 1)
    if len(user_part) <= 2:
        masked_user = user_part[0] + "*"
    else:
        masked_user = user_part[0] + "*" * (len(user_part) - 2) + user_part[-1]
    return f"{masked_user}@{domain_part}"


@app.route("/forgot-password/verify", methods=["GET", "POST"])
def verify_forgot_password_otp():
    if not is_gmail_enabled():
        flash("Email service is disabled in local mode.", "warning")
        return redirect(url_for("login"))

    email = session.get("reset_email")
    user_id = session.get("reset_user_id")
    username = session.get("reset_username")
    role = session.get("reset_role")

    if not email or not user_id:
        flash("No active password recovery session. Please enter your username or email.", "warning")
        return redirect(url_for("forgot_password"))

    masked = mask_email(email)

    if request.method == "POST":
        action_type = request.form.get("action_type", "onetime_login")
        otp_code = request.form.get("otp_code", "").strip()

        is_valid, msg, payload, verified_uid = default_otp_manager.verify_otp(
            email, otp_code, purpose="password_reset"
        )

        if not is_valid:
            flash(msg, "danger")
            return render_template("forgot_password_verify.html", email=email, masked_email=masked)

        actual_user_id = verified_uid or user_id
        actual_username = (payload and payload.get("username")) or username
        actual_role = (payload and payload.get("role")) or role

        if action_type == "onetime_login":
            sid = str(uuid.uuid4())
            session["sid"] = sid
            session["user_id"] = actual_user_id
            session["username"] = actual_username
            session["role"] = actual_role
            cipher_store[sid] = None

            # Clear recovery session vars
            session.pop("reset_email", None)
            session.pop("reset_user_id", None)
            session.pop("reset_username", None)
            session.pop("reset_role", None)

            flash("✅ Logged in successfully via one-time security code.", "success")
            return redirect(url_for("dashboard"))

        elif action_type == "reset_password":
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            if not new_password or not confirm_password:
                flash("Please enter and confirm your new password.", "warning")
                return render_template("forgot_password_verify.html", email=email, masked_email=masked)

            if new_password != confirm_password:
                flash("Passwords do not match. Please re-enter.", "danger")
                return render_template("forgot_password_verify.html", email=email, masked_email=masked)

            if len(new_password) < 6:
                flash("New master password must be at least 6 characters.", "warning")
                return render_template("forgot_password_verify.html", email=email, masked_email=masked)

            update_ok, update_msg = update_user_password(actual_user_id, new_password)
            if not update_ok:
                flash(f"Failed to update password: {update_msg}", "danger")
                return render_template("forgot_password_verify.html", email=email, masked_email=masked)

            # Send alert email
            send_password_changed_notification(to_email=email, username=actual_username)

            # Derive cipher with the new password and log user in
            try:
                cipher = get_cipher_for_user(actual_user_id, new_password)
            except Exception:
                cipher = None

            sid = str(uuid.uuid4())
            session["sid"] = sid
            session["user_id"] = actual_user_id
            session["username"] = actual_username
            session["role"] = actual_role
            if cipher:
                cipher_store[sid] = cipher

            session.pop("reset_email", None)
            session.pop("reset_user_id", None)
            session.pop("reset_username", None)
            session.pop("reset_role", None)

            flash("🎉 Master password updated successfully! You are now logged in.", "success")
            return redirect(url_for("dashboard"))

    return render_template("forgot_password_verify.html", email=email, masked_email=masked)


@app.route("/forgot-password/resend", methods=["POST"])
def resend_forgot_password_otp():
    if not is_gmail_enabled():
        flash("Email service is disabled in local mode.", "warning")
        return redirect(url_for("login"))

    email = session.get("reset_email")
    user_id = session.get("reset_user_id")
    username = session.get("reset_username", "User")
    role = session.get("reset_role", "user")

    if not email or not user_id:
        flash("No active recovery request. Please enter your email again.", "warning")
        return redirect(url_for("forgot_password"))

    payload = {"user_id": user_id, "username": username, "email": email, "role": role}
    ok, otp_code, _ = default_otp_manager.create_otp(
        email=email,
        purpose="password_reset",
        user_id=user_id,
        payload=payload
    )

    if ok:
        send_ok, send_msg = send_password_reset_otp_email(to_email=email, username=username, otp_code=otp_code)
        if send_ok:
            flash(f"A new security code has been sent to your email.", "info")
        else:
            flash(f"Failed to send email: {send_msg}", "danger")
    else:
        flash("Failed to generate a new security code.", "danger")

    return redirect(url_for("verify_forgot_password_otp"))


@app.route("/logout")
@require_login
def logout():
    clear_session_cipher()
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))

# --- Google OAuth Routes ---
@app.route("/login/google")
def google_login():
    if not is_google_oauth_enabled():
        flash("Google OAuth login is disabled in local mode.", "warning")
        return redirect(url_for("login"))

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&state={state}"
    )
    return redirect(auth_url)

@app.route("/callback/google")
def google_callback():
    if not is_google_oauth_enabled():
        flash("Google OAuth login is disabled in local mode.", "warning")
        return redirect(url_for("login"))
    state = request.args.get("state")
    if state != session.get("oauth_state"):
        flash("Invalid OAuth state.", "danger")
        return redirect(url_for("login"))
    
    code = request.args.get("code")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # 1. Exchange code for token
    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    })
    
    if token_resp.status_code != 200:
        flash("Failed to authenticate with Google.", "danger")
        return redirect(url_for("login"))
        
    token_json = token_resp.json()
    id_token = token_json.get("id_token")
    
    # 2. Verify token (simplest way: use userinfo endpoint with access_token)
    access_token = token_json.get("access_token")
    user_info_resp = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers={
        "Authorization": f"Bearer {access_token}"
    })
    
    if user_info_resp.status_code != 200:
        flash("Failed to get user info from Google.", "danger")
        return redirect(url_for("login"))
    
    user_info = user_info_resp.json()
    google_sub = user_info["id"]
    email = user_info["email"]
    name = user_info["name"]
    
    # 3. DB logic: find or create google_db/user
    conn = get_connection()
    cur = conn.cursor()
    
    # Check if google account exists
    cur.execute("SELECT user_id FROM google_db WHERE google_subject = %s", (google_sub,))
    google_record = cur.fetchone()
    
    if google_record:
        user_id = google_record[0]
        cur.execute("SELECT username, role FROM users WHERE user_id = %s", (user_id,))
        user_record = cur.fetchone()
        username = user_record[0]
        role = user_record[1]
    else:
        # Create or link user
        cur.execute("SELECT user_id, username, role FROM users WHERE email = %s", (email,))
        user_record = cur.fetchone()
        
        if user_record:
            # Link existing user
            user_id, username, role = user_record
        else:
            # Create new user
            username = email.split("@")[0] # Simple username
            # We need a dummy password hash
            import bcrypt
            hashed = bcrypt.hashpw(secrets.token_urlsafe(16).encode(), bcrypt.gensalt()).decode()
            cur.execute("INSERT INTO users (username, email, master_password_hash, role) VALUES (%s, %s, %s, 'user')", 
                        (username, email, hashed))
            user_id = cur.lastrowid
            role = 'user'
            
        # Create google link
        cur.execute("INSERT INTO google_db (user_id, google_subject, google_email, google_name) VALUES (%s, %s, %s, %s)",
                    (user_id, google_sub, email, name))
        conn.commit()

    # 4. Session setup
    sid = str(uuid.uuid4())
    session["sid"] = sid
    session["user_id"] = user_id
    session["username"] = username
    session["role"] = role
    
    # Since OAuth users don't have a master key for encryption initially, we'll need to check
    # how to handle their vault/passwords. 
    # For now, we set them up with NO cipher or handle migration in helper
    # The requirement is that they have access to their dashboard, but existing 
    # encryption logic might break without a cipher.
    
    cur.close()
    conn.close()
    
    flash("Logged in with Google.", "success")
    return redirect(url_for("dashboard"))


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
        
        pw = decrypt_password_for_view(role, admin_cipher, user_cipher, enc_admin, enc_user, owner_uid, pid, session.get("user_id"))

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

@app.route("/search")
@require_login
def global_search():
    user_id = session["user_id"]
    role = session["role"]
    user_cipher = get_cipher_for_session()
    
    try:
        admin_cipher = get_admin_cipher()
    except Exception:
        admin_cipher = None

    q = request.args.get("q", "").strip().lower()
    
    if not q:
        return render_template("search_results.html", query=q, passwords=[], role=role)

    # Permission check for global search
    if role == "admin":
        base_sql = """
            SELECT p.password_id, p.user_id, u.username,
                   p.service_name, p.username,
                   p.password_user_enc, p.password_admin_enc,
                   p.url, p.notes, p.updated_at,
                   v.vault_name, v.vault_id
            FROM passwords p 
            JOIN users u ON p.user_id = u.user_id
            JOIN vaults v ON p.vault_id = v.vault_id
            WHERE p.is_deleted = 0 AND v.is_deleted = 0
        """
        params = ()
    else:
        base_sql = """
            SELECT p.password_id, p.user_id, u.username, 
                   p.service_name, p.username,
                   p.password_user_enc, p.password_admin_enc,
                   p.url, p.notes, p.updated_at,
                   v.vault_name, v.vault_id
            FROM passwords p
            JOIN users u ON p.user_id = u.user_id
            JOIN vaults v ON p.vault_id = v.vault_id
            WHERE p.user_id = %s AND p.is_deleted = 0 AND v.is_deleted = 0
        """
        params = (user_id,)

    rows = query_all(base_sql, params)
    
    # Decrypt and filter in one pass
    passwords = []
    for r in rows:
        pid, owner_uid, owner_username, service, uname, enc_user, enc_admin, url, notes, updated_at, vault_name, vault_id = r
        
        # safely handle nones
        owner_name_str = (owner_username or "").lower()
        service_str = (service or "").lower()
        username_str = (uname or "").lower()
        url_str = (url or "").lower()
        notes_str = (notes or "").lower()
        vault_name_str = (vault_name or "").lower()
        
        pw = decrypt_password_for_view(role, admin_cipher, user_cipher, enc_admin, enc_user, owner_uid, pid, session.get("user_id"))
        pw_str = (pw or "").lower()
        
        if (q in owner_name_str or q in service_str or q in username_str or 
            q in url_str or q in notes_str or q in vault_name_str or q in pw_str):
            
            passwords.append({
                "password_id": pid,
                "owner_username": owner_username,
                "service": service,
                "username": uname,
                "password": pw,
                "url": url,
                "notes": notes,
                "updated_at": updated_at,
                "vault_name": vault_name,
                "vault_id": vault_id
            })

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"passwords": passwords, "role": role}

    return render_template("search_results.html", query=q, passwords=passwords, role=role)

@app.route("/admin/passwords/<int:password_id>/edit", methods=["GET", "POST"])
@require_login
def admin_edit_password(password_id):
    if session.get("role") != "admin":
        flash("Admins only.", "danger")
        return redirect(url_for("dashboard"))
    
    conn = get_connection()
    cur = conn.cursor()
    
    if request.method == "GET":
        cur.execute("SELECT service_name, username, url, notes, password_admin_enc FROM passwords WHERE password_id = %s", (password_id,))
        row = cur.fetchone()
        if not row:
            flash("Password not found.", "danger")
            return redirect(url_for("dashboard"))
            
        old_pw = ""
        try:
            admin_cipher = get_admin_cipher()
            if row[4] and admin_cipher:
                old_pw = admin_cipher.decrypt(row[4].encode()).decode()
        except:
            old_pw = "[Cannot decrypt]"
        
        p = {
            "service_name": row[0],
            "username": row[1],
            "url": row[2],
            "notes": row[3],
            "password": old_pw
        }
        cur.close()
        conn.close()
        return render_template("admin_edit_password.html", p=p)
        
    elif request.method == "POST":
        service = request.form.get("service_name", "").strip()
        username = request.form.get("username", "").strip()
        url_field = request.form.get("url", "").strip()
        notes = request.form.get("notes", "").strip()
        new_password = request.form.get("password", "")
        
        try:
            admin_cipher = get_admin_cipher()
        except:
            admin_cipher = None
            
        cur.execute("SELECT password_admin_enc FROM passwords WHERE password_id = %s", (password_id,))
        old_row = cur.fetchone()
        old_pw = ""
        if old_row and old_row[0] and admin_cipher:
            try:
                old_pw = admin_cipher.decrypt(old_row[0].encode()).decode()
            except:
                old_pw = "[Could not decrypt]"
            
        if new_password and admin_cipher:
            enc_admin = admin_cipher.encrypt(new_password.encode()).decode()
            cur.execute("""
                UPDATE passwords 
                SET service_name=%s, username=%s, url=%s, notes=%s, password_admin_enc=%s, password_user_enc=NULL
                WHERE password_id=%s
            """, (service, username, url_field, notes, enc_admin, password_id))
        else:
            cur.execute("""
                UPDATE passwords 
                SET service_name=%s, username=%s, url=%s, notes=%s
                WHERE password_id=%s
            """, (service, username, url_field, notes, password_id))
            
        conn.commit()
        cur.close()
        conn.close()
        
        log_entry = {
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "admin": session.get('username'),
            "password_id": password_id,
            "service": service,
            "old_password": old_pw if old_pw else "[No Previous Password Found]",
            "new_password": new_password if new_password else "[Unchanged]",
            "local_ip": request.remote_addr,
            "public_ip": request.headers.get("X-Forwarded-For", request.remote_addr)
        }
        
        with open("admin_audit.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        flash("Password updated successfully.", "success")
        return redirect(url_for("global_search"))

@app.route("/admin/logs")
@require_login
def admin_logs():
    if session.get("role") != "admin":
        flash("Admins only.", "danger")
        return redirect(url_for("dashboard"))
    
    logs = []
    if os.path.exists("admin_audit.jsonl"):
        with open("admin_audit.jsonl", "r") as f:
            for line in f:
                if line.strip():
                    try:
                        logs.append(json.loads(line))
                    except:
                        pass
                        
    # For legacy logs
    if os.path.exists("admin_audit.log"):
        with open("admin_audit.log", "r") as f:
            for line in f:
                if line.strip():
                    logs.append({"raw_legacy": line.strip()})
            
    logs.reverse()
    return render_template("admin_logs.html", logs=logs)

# Add vault
@app.route("/manifest.json")
def manifest():
    return send_from_directory("templates", "manifest.json")

@app.route("/sw.js")
def sw():
    return send_from_directory("templates", "sw.js")

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
    flash("Password moved to trash.", "info")
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

# -------------------------
# Admin-only Vault Soft Delete/Restore Routes
# -------------------------

# Soft delete vault (admin only)
@app.route("/vaults/<int:vault_id>/soft_delete", methods=["POST"])
@require_login
def soft_delete_vault_route(vault_id):
    if session.get("role") != "admin":
        abort(403)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Check vault exists
    cur.execute("SELECT vault_name FROM vaults WHERE vault_id = %s", (vault_id,))
    vault = cur.fetchone()
    
    if not vault:
        flash("Vault not found.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("dashboard"))
    
    # Soft delete the vault
    cur.execute(
        "UPDATE vaults SET is_deleted = 1, updated_at = NOW() WHERE vault_id = %s",
        (vault_id,)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f"Vault '{vault[0]}' moved to trash.", "info")
    return redirect(request.referrer or url_for("dashboard"))

# Restore vault (admin only)
@app.route("/vaults/<int:vault_id>/restore", methods=["POST"])
@require_login
def restore_vault_route(vault_id):
    if session.get("role") != "admin":
        abort(403)
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Check vault exists
    cur.execute("SELECT vault_name FROM vaults WHERE vault_id = %s AND is_deleted = 1", (vault_id,))
    vault = cur.fetchone()
    
    if not vault:
        flash("Vault not found in trash.", "danger")
        cur.close()
        conn.close()
        return redirect(url_for("trash_vaults"))
    
    # Restore the vault
    cur.execute(
        "UPDATE vaults SET is_deleted = 0, updated_at = NOW() WHERE vault_id = %s",
        (vault_id,)
    )
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f"Vault '{vault[0]}' restored.", "success")
    return redirect(request.referrer or url_for("trash_vaults"))

# List deleted vaults (admin only)
@app.route("/admin/trash/vaults")
@require_login
def trash_vaults():
    if session.get("role") != "admin":
        abort(403)
    
    q = request.args.get("q", "").strip().lower()
    
    # Get all soft-deleted vaults
    rows = query_all("""
        SELECT v.vault_id, v.vault_name, v.description, u.username, v.updated_at
        FROM vaults v
        JOIN users u ON v.user_id = u.user_id
        WHERE v.is_deleted = 1
        ORDER BY v.updated_at DESC
    """)
    
    # Filter if search is provided
    if q:
        rows = [
            r for r in rows
            if q in r[1].lower()      # vault_name
            or (r[2] and q in r[2].lower())      # description
            or q in r[3].lower()      # owner username
        ]
    
    return render_template("trash_vaults.html", vaults=rows, q=q)

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
        success, msg = register_user(username, email, password, role)
        if not success:
            flash(f"Could not create user: {msg}", "danger")
            return redirect(url_for("admin_add_user"))

        flash("User created successfully!", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_add_user.html")

@app.route("/admin/users/<int:user_id>/edit", methods=["GET"])
@require_login
def modify_user(user_id):
    if session.get("role") != "admin":
        abort(403)

    user = query_one(
        "SELECT user_id, username, email, role, status FROM users WHERE user_id = %s",
        (user_id,)
    )

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin_users"))

    return render_template("modify_user.html", user=user)

import bcrypt

@app.route("/admin/users/<int:user_id>/edit", methods=["POST"])
@require_login
def admin_update_user(user_id):
    if session.get("role") != "admin":
        abort(403)

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "").strip()
    status = request.form.get("status", "").strip()
    new_password = request.form.get("new_password", "").strip()

    if not username or not email or not role or not status:
        flash("All fields except password are required.", "warning")
        return redirect(url_for("admin_edit_user", user_id=user_id))

    conn = get_connection()
    cur = conn.cursor()

    # Update base user info
    cur.execute("""
        UPDATE users SET username=%s, email=%s, role=%s, status=%s
        WHERE user_id=%s
    """, (username, email, role, status, user_id))

    # Password reset (optional)
    if new_password:
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

        # Regenerate salt for the user (new salt → new derived key)
        new_salt = os.urandom(16)

        cur.execute(
            "UPDATE users SET master_password_hash=%s, salt=%s WHERE user_id=%s",
            (hashed, new_salt.hex(), user_id)
        )

        flash("User password reset and key regenerated.", "info")
    else:
        flash("User updated successfully.", "success")

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("admin_users"))



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
        # Use uploaded (FileStorage) directly, not uploaded.stream
        df = pd.read_excel(uploaded)
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
    app.run(debug=True,host='0.0.0.0',port=5000)
