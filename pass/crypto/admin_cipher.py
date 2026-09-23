import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

def get_admin_cipher():
    # 1. Check environment variable entirely first
    env_key = os.getenv("ADMIN_GLOBAL_KEY")
    if env_key:
        return Fernet(env_key.encode())
        
    # 2. Fallback to physical .key file
    key_path = os.path.join(os.path.dirname(__file__), "global_admin.key")
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read()
        return Fernet(key)
        
    raise FileNotFoundError("No Admin Global Key found in .env or global_admin.key file")
