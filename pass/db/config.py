import os

DB_CONFIG = {
    "host": "localhost",
    "user": "pass",
    "password": os.getenv("PASSWORD_MANAGER_DB_PASSWORD", "password@321"),
    "database": "password",
    "port": 3306
}
