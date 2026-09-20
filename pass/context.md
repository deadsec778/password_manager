Absolutely bro — here is a **clean, short, precise, professional project summary** you can give to ANY AI for debugging, continuation, or development.

This summary includes:

✔ Architecture
✔ Folder structure
✔ Crypto system
✔ DB schema
✔ Features built
✔ What’s working
✔ What’s pending

Use this as your **project context file**.

---

# 🚀 **PASSWORD MANAGER — CURRENT PROJECT CONTEXT (BRIEF + COMPLETE)**

## 📌 OVERVIEW

I am building a **self-hosted LAN-based password manager** using **Python, MySQL (MariaDB), Flask, and CLI**.
The system includes:

* User management
* Vault management
* Password storage
* Per-user encryption
* RBAC (admin/user roles)
* Soft delete + restore + purge
* Hard delete
* Flask test UI
* CLI utilities

This is an ongoing project, not yet production-ready.

---

# 📂 **PROJECT FOLDER STRUCTURE**

```
pass_venv/
│   __init__.py
│
├── api/
│   ├── __init__.py
│   └── login_test.py
│
├── users/
│   ├── __init__.py
│   ├── register_user.py
│   ├── login_user.py
│   ├── soft_delete_user.py
│   ├── restore_user.py
│   ├── hard_delete_user.py
│   ├── list_deleted_users.py
│   └── purge_deleted_users.py
│
├── vaults/
│   ├── __init__.py
│   ├── add_vault.py
│   ├── list_vaults.py
│   ├── soft_delete_vault.py
│   ├── restore_vault.py
│   ├── hard_delete_vault.py
│   ├── list_deleted_vaults.py
│   └── purge_deleted_vaults.py
│
├── passwords/
│   ├── __init__.py
│   ├── add_password.py
│   ├── list_passwords_by_vault.py
│   ├── soft_delete_password.py
│   ├── restore_password.py
│   ├── hard_delete_password.py
│   ├── list_deleted_passwords.py
│   └── purge_deleted_passwords.py
│
├── crypto/
│   ├── __init__.py
│   └── crypto_key.py
│
├── db/
│   ├── __init__.py
│   ├── config.py
│   └── connection.py
│
└── utils/
    └── __init__.py
```

---

# 🛢️ **DATABASE SCHEMA (SHORT SUMMARY)**

### `users` table

```
user_id (PK, auto)
username (unique)
email
master_password_hash (bcrypt)
salt (per-user PBKDF2 salt)
role ENUM('admin','user')
status ENUM('active','disabled')
is_deleted TINYINT (soft delete)
created_at
last_login
```

### `vaults` table

```
vault_id (PK)
user_id (FK)
vault_name
description
is_deleted TINYINT
created_at
updated_at
```

### `passwords` table

```
password_id (PK)
vault_id (FK)
user_id (FK)
service_name
username
password_encrypted  (Fernet encrypted)
url
notes
is_deleted TINYINT
created_at
updated_at
last_accessed
```

---

# 🔐 **CRYPTOGRAPHY SYSTEM**

### ✔ Uses PBKDF2 + SHA256 key derivation

Key = PBKDF2(master_password, salt, 390000 rounds)

### ✔ Per-user salt stored in `users.salt`

### ✔ Fernet used for AES-128 encryption

All password encryption = Fernet(key)

### ✔ Key derived at login

Login returns:

```
user_id, role, cipher
```

### ❌ No global secret.key (removed)

### ✔ Zero-knowledge encryption

---

# 🔑 **AUTH / LOGIN SYSTEM**

`login_user.py`:

* Checks bcrypt hash
* Updates last_login
* Derives cipher using get_cipher_for_user()
* Returns `(user_id, role, cipher)`

Used in both CLI + Flask.

---

# 🔒 **RBAC — ROLE-BASED ACCESS CONTROL**

### Admin:

* View all users
* View all vaults
* View all passwords
* Soft-delete, restore, purge any entry
* Hard delete
* Manage everything

### User:

* Only see their own vaults
* Only see their own passwords
* Only delete/restore/update their own entries

All vault + password functions include role checks.

---

# 🗑️ **SOFT DELETE SYSTEM (Trash Bin)**

### EVERY module (users, vaults, passwords) has:

* soft_delete
* restore
* list_deleted
* purge_deleted
* hard_delete

Implemented consistently across all modules.

---

# 🌐 **FLASK TEST UI**

Basic test endpoint exists:

```
api/login_test.py
```

* Simple HTML login page
* Tests bcrypt + PBKDF2 + cipher generation
* Confirms DB connection + authentication

This is not the final UI.

---

# 📝 **CURRENT STATUS (as of now)**

### ✔ User registration works

### ✔ Login with cipher generation works

### ✔ Per-user encryption works

### ✔ All CRUD for passwords works

### ✔ All CRUD for vaults works

### ✔ Soft delete system works

### ✔ Project imports fixed (sys.path, root **init**)

### ✔ Flask test login works

### ⚠️ CLI not built yet

### ⚠️ Full Flask UI not built yet

### ⚠️ Admin recovery key not implemented (optional)

### ⚠️ Optimization and polishing pending

---

# 🎯 **WHAT IS NEXT? (Pick one)**

**A)** Build Flask dashboard after login (vaults, passwords, role-based menu)
**B)** Build complete CLI system
**C)** Build full REST API with tokens
**D)** Add Admin Recovery Key (optional security feature)
**E)** Optimize project structure + imports
**F)** Add session-based login in Flask (Flask-Login)

---

# 🔥 This is the exact project context you can give to any AI.

Just copy-paste the whole context above to any model and it will instantly understand the project.

---

When you’re ready, tell me:

👉 **A, B, C, D, E or F**
and we’ll continue building.
