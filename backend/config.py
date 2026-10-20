import os


class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "change-this-to-a-secure-secret-key"
    )


    # =====================================================
    # DATABASE CONFIGURATION
    # =====================================================

    MYSQL_HOST = "127.0.0.1"

    MYSQL_USER = "root"

    MYSQL_PASSWORD = ""

    MYSQL_DB = "gazz_pos_inventory"

    MYSQL_PORT = 3307

    MYSQL_CURSORCLASS = "DictCursor"


    # =====================================================
    # OPTIONAL ALIASES
    # =====================================================

    DB_HOST = MYSQL_HOST

    DB_USER = MYSQL_USER

    DB_PASSWORD = MYSQL_PASSWORD

    DB_NAME = MYSQL_DB

    DB_PORT = MYSQL_PORT