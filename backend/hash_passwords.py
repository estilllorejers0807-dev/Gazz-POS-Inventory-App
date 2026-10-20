import sys
import os
import bcrypt

# Add parent directory to path to access database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.connection import mysql

accounts = [
    ("manager", "admin123"),
    ("cashier01", "cashier123"),
    ("attendant01", "attendant123")
]

with app.app_context():
    cursor = mysql.connection.cursor()

    for username, password in accounts:
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE username = %s",
            (password_hash, username)
        )

    mysql.connection.commit()
    cursor.close()

print("Passwords were securely converted to bcrypt hashes.")