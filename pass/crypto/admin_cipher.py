import os
from cryptography.fernet import Fernet

def get_admin_cipher():
    # Use absolute path relative to this file's location
    key_path = os.path.join(os.path.dirname(__file__), "global_admin.key")
    with open(key_path, "rb") as f:
        key = f.read()
    return Fernet(key)
