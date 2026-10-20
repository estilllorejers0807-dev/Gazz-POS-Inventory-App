from flask import (
    Blueprint,
    jsonify
)

from flask_login import current_user

from database.connection import mysql


api_admin_bp = Blueprint(
    "api_admin",
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
# ADMIN DASHBOARD
# GET /api/admin/dashboard
# =========================================================

@api_admin_bp.route(
    "/dashboard",
    methods=["GET"]
)
def dashboard():

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

        # =================================================
        # TOTAL USERS
        # =================================================

        cursor.execute("""
            SELECT
                COUNT(*) AS total_users
            FROM users
        """)

        result = cursor.fetchone()

        total_users = (
            result["total_users"]
            if result
            else 0
        )


        # =================================================
        # ACTIVE USERS
        # =================================================

        cursor.execute("""
            SELECT
                COUNT(*) AS active_users
            FROM users
            WHERE is_active = 1
        """)

        result = cursor.fetchone()

        active_users = (
            result["active_users"]
            if result
            else 0
        )


        # =================================================
        # INACTIVE USERS
        # =================================================

        cursor.execute("""
            SELECT
                COUNT(*) AS inactive_users
            FROM users
            WHERE is_active = 0
        """)

        result = cursor.fetchone()

        inactive_users = (
            result["inactive_users"]
            if result
            else 0
        )


        # =================================================
        # ACTIVE PRODUCTS
        # =================================================

        cursor.execute("""
            SELECT
                COUNT(*) AS total_products
            FROM products
            WHERE is_active = 1
        """)

        result = cursor.fetchone()

        total_products = (
            result["total_products"]
            if result
            else 0
        )


        # =================================================
        # USERS BY ROLE
        # =================================================

        cursor.execute("""
            SELECT
                role,
                COUNT(*) AS total

            FROM users

            GROUP BY role

            ORDER BY role
        """)

        role_rows = cursor.fetchall()

        users_by_role = []

        for row in role_rows:

            users_by_role.append({
                "role":
                    row["role"],

                "total":
                    int(row["total"])
            })


        return jsonify({
            "success": True,

            "dashboard": {
                "total_users":
                    int(total_users),

                "active_users":
                    int(active_users),

                "inactive_users":
                    int(inactive_users),

                "total_products":
                    int(total_products),

                "users_by_role":
                    users_by_role
            }

        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not load admin dashboard.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()