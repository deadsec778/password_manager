import os
from dotenv import load_dotenv

# Load .env from the pass/ root (one level up from db/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "127.0.0.1"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER", "pass"),
    "password": os.getenv("DB_PASSWORD", "password@321"),
    "database": os.getenv("DB_NAME", "password"),
}
