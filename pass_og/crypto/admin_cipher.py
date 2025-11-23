from cryptography.fernet import Fernet

def get_admin_cipher():
    with open("crypto/global_admin.key", "rb") as f:
        key = f.read()
    return Fernet(key)
