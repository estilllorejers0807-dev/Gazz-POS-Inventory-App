from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, current_user
import bcrypt

from database.connection import mysql


api_auth_bp = Blueprint(
    "api_auth",
    __name__
)


# =========================================================
# API LOGIN
# POST /api/auth/login
# =========================================================

@api_auth_bp.route(
    "/login",
    methods=["POST"]
)
def api_login():

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    username = data.get(
        "username",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    )

    if not username or not password:

        return jsonify({
            "success": False,
            "message": "Username and password are required."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                user_id,
                username,
                password_hash,
                full_name,
                role

            FROM users

            WHERE
                username = %s
                AND is_active = 1
            """,
            (username,)
        )

        user_data = cursor.fetchone()

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Database error.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()

    if not user_data:

        return jsonify({
            "success": False,
            "message": "Invalid username or password."
        }), 401

    stored_hash = user_data["password_hash"]

    if not bcrypt.checkpw(
        password.encode("utf-8"),
        stored_hash.encode("utf-8")
    ):

        return jsonify({
            "success": False,
            "message": "Invalid username or password."
        }), 401

    # Import here to avoid circular import
    from app import User

    user = User(
        user_data["user_id"],
        user_data["username"],
        user_data["role"],
        user_data["full_name"]
    )

    login_user(user)

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role
        }
    }), 200


# =========================================================
# API LOGOUT
# POST /api/auth/logout
# =========================================================

@api_auth_bp.route(
    "/logout",
    methods=["POST"]
)
def api_logout():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "No user is currently logged in."
        }), 401

    logout_user()

    return jsonify({
        "success": True,
        "message": "Logout successful."
    }), 200


# =========================================================
# CURRENT USER
# GET /api/auth/me
# =========================================================

@api_auth_bp.route(
    "/me",
    methods=["GET"]
)
def api_current_user():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    return jsonify({
        "success": True,
        "user": {
            "user_id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "role": current_user.role
        }
    }), 200