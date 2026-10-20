from flask import (
    Blueprint,
    jsonify,
    request
)

from flask_login import current_user

import bcrypt

from database.connection import mysql


api_users_bp = Blueprint(
    "api_users",
    __name__
)


# =========================================================
# ADMIN CHECK
# =========================================================

def admin_access():

    return (
        current_user.is_authenticated
        and current_user.role == "admin"
    )


# =========================================================
# ALLOWED ROLES
# =========================================================

ALLOWED_ROLES = (
    "admin",
    "manager",
    "store_cashier",
    "fuel_cashier",
    "attendant"
)


# =========================================================
# GET USERS
# GET /api/users
# =========================================================

@api_users_bp.route(
    "/",
    methods=["GET"]
)
def get_users():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not admin_access():

        return jsonify({
            "success": False,
            "message": (
                "Administrator access required."
            )
        }), 403

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                user_id,
                username,
                full_name,
                role,
                is_active

            FROM users

            ORDER BY user_id ASC
        """)

        rows = cursor.fetchall()

        users = []

        for row in rows:

            users.append({
                "user_id":
                    row["user_id"],

                "username":
                    row["username"],

                "full_name":
                    row["full_name"],

                "role":
                    row["role"],

                "is_active":
                    bool(
                        row["is_active"]
                    )
            })


        cursor.execute("""
            SELECT

                COUNT(*) AS total_users,

                SUM(
                    CASE
                        WHEN is_active = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS active_users,

                SUM(
                    CASE
                        WHEN is_active = 0
                        THEN 1
                        ELSE 0
                    END
                ) AS inactive_users

            FROM users
        """)

        summary = cursor.fetchone()


        return jsonify({
            "success": True,

            "users": users,

            "summary": {
                "total_users":
                    int(
                        summary[
                            "total_users"
                        ] or 0
                    ),

                "active_users":
                    int(
                        summary[
                            "active_users"
                        ] or 0
                    ),

                "inactive_users":
                    int(
                        summary[
                            "inactive_users"
                        ] or 0
                    )
            }

        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not load users.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# GET ONE USER
# GET /api/users/<user_id>
# =========================================================

@api_users_bp.route(
    "/<int:user_id>",
    methods=["GET"]
)
def get_user(user_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not admin_access():

        return jsonify({
            "success": False,
            "message": (
                "Administrator access required."
            )
        }), 403

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                user_id,
                username,
                full_name,
                role,
                is_active

            FROM users

            WHERE user_id = %s
        """, (
            user_id,
        ))

        user = cursor.fetchone()

        if not user:

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        return jsonify({
            "success": True,
            "user": {
                "user_id":
                    user["user_id"],

                "username":
                    user["username"],

                "full_name":
                    user["full_name"],

                "role":
                    user["role"],

                "is_active":
                    bool(
                        user["is_active"]
                    )
            }
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not retrieve user.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# CREATE USER
# POST /api/users
# =========================================================

@api_users_bp.route(
    "/",
    methods=["POST"]
)
def create_user():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not admin_access():

        return jsonify({
            "success": False,
            "message": (
                "Administrator access required."
            )
        }), 403

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    username = data.get(
        "username",
        ""
    ).strip()

    full_name = data.get(
        "full_name",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    )

    role = data.get(
        "role",
        "store_cashier"
    ).strip()

    if not username or not full_name or not password:

        return jsonify({
            "success": False,
            "message": (
                "Username, full name, and password "
                "are required."
            )
        }), 400

    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": (
                "Password must contain at least "
                "6 characters."
            )
        }), 400

    if role not in ALLOWED_ROLES:

        return jsonify({
            "success": False,
            "message": "Invalid user role."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                user_id

            FROM users

            WHERE username = %s
        """, (
            username,
        ))

        if cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "Username already exists."
            }), 409

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute("""
            INSERT INTO users
            (
                username,
                password_hash,
                full_name,
                role,
                is_active
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                1
            )
        """, (
            username,
            hashed_password,
            full_name,
            role
        ))

        user_id = cursor.lastrowid

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "User created successfully.",
            "user_id": user_id
        }), 201

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not create user.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# UPDATE USER
# PUT /api/users/<user_id>
# =========================================================

@api_users_bp.route(
    "/<int:user_id>",
    methods=["PUT"]
)
def update_user(user_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not admin_access():

        return jsonify({
            "success": False,
            "message": (
                "Administrator access required."
            )
        }), 403

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    username = data.get(
        "username",
        ""
    ).strip()

    full_name = data.get(
        "full_name",
        ""
    ).strip()

    role = data.get(
        "role",
        ""
    ).strip()

    if not username or not full_name or not role:

        return jsonify({
            "success": False,
            "message": (
                "Username, full name, and role "
                "are required."
            )
        }), 400

    if role not in ALLOWED_ROLES:

        return jsonify({
            "success": False,
            "message": "Invalid user role."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                user_id

            FROM users

            WHERE user_id = %s
        """, (
            user_id,
        ))

        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        cursor.execute("""
            SELECT
                user_id

            FROM users

            WHERE
                username = %s
                AND user_id != %s
        """, (
            username,
            user_id
        ))

        if cursor.fetchone():

            return jsonify({
                "success": False,
                "message": (
                    "Username is already being "
                    "used by another account."
                )
            }), 409

        cursor.execute("""
            UPDATE users

            SET
                username = %s,
                full_name = %s,
                role = %s

            WHERE
                user_id = %s
        """, (
            username,
            full_name,
            role,
            user_id
        ))

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "User updated successfully."
        }), 200

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not update user.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# CHANGE PASSWORD
# PUT /api/users/<user_id>/password
# =========================================================

@api_users_bp.route(
    "/<int:user_id>/password",
    methods=["PUT"]
)
def change_password(user_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not admin_access():

        return jsonify({
            "success": False,
            "message": (
                "Administrator access required."
            )
        }), 403

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    password = data.get(
        "password",
        ""
    )

    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": (
                "Password must contain at least "
                "6 characters."
            )
        }), 400

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                user_id

            FROM users

            WHERE user_id = %s
        """, (
            user_id,
        ))

        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute("""
            UPDATE users

            SET
                password_hash = %s

            WHERE
                user_id = %s
        """, (
            hashed_password,
            user_id
        ))

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Password updated successfully."
        }), 200

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not change password.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# ACTIVATE USER
# PATCH /api/users/<user_id>/activate
# =========================================================

@api_users_bp.route(
    "/<int:user_id>/activate",
    methods=["PATCH"]
)
def activate_user(user_id):

    return set_user_status(
        user_id,
        1
    )


# =========================================================
# DEACTIVATE USER
# PATCH /api/users/<user_id>/deactivate
# =========================================================

@api_users_bp.route(
    "/<int:user_id>/deactivate",
    methods=["PATCH"]
)
def deactivate_user(user_id):

    if user_id == current_user.id:

        return jsonify({
            "success": False,
            "message": (
                "You cannot deactivate "
                "your own administrator account."
            )
        }), 400

    return set_user_status(
        user_id,
        0
    )


# =========================================================
# USER STATUS HELPER
# =========================================================

def set_user_status(
    user_id,
    status
):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not admin_access():

        return jsonify({
            "success": False,
            "message": (
                "Administrator access required."
            )
        }), 403

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                user_id

            FROM users

            WHERE user_id = %s
        """, (
            user_id,
        ))

        if not cursor.fetchone():

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        cursor.execute("""
            UPDATE users

            SET
                is_active = %s

            WHERE
                user_id = %s
        """, (
            status,
            user_id
        ))

        mysql.connection.commit()

        action = (
            "activated"
            if status == 1
            else "deactivated"
        )

        return jsonify({
            "success": True,
            "message": (
                f"User account {action} successfully."
            )
        }), 200

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not update user status.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()