from flask import Blueprint, render_template
from flask_login import login_required, current_user

from database.connection import mysql


# =========================================================
# ADMIN BLUEPRINT
# =========================================================

admin_bp = Blueprint(
    "admin",
    __name__
)


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@admin_bp.route("/admin/dashboard")
@login_required
def admin_dashboard():

    # =====================================================
    # ADMIN ONLY
    # =====================================================

    if current_user.role != "admin":

        return (
            "Access Denied: Administrator access required.",
            403
        )


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
        # USER ROLES
        #
        # This gives the administrator a simple overview
        # of how many accounts exist for each role.
        # =================================================

        cursor.execute("""
            SELECT
                role,
                COUNT(*) AS total
            FROM users
            GROUP BY role
            ORDER BY
                CASE role
                    WHEN 'admin' THEN 1
                    WHEN 'manager' THEN 2
                    WHEN 'store_cashier' THEN 3
                    WHEN 'fuel_cashier' THEN 4
                    WHEN 'attendant' THEN 5
                    ELSE 6
                END
        """)

        users_by_role = cursor.fetchall()


    except Exception as error:

        print(
            f"Admin Dashboard SQL Error: {error}"
        )


        total_users = 0

        active_users = 0

        inactive_users = 0

        total_products = 0

        users_by_role = []


    finally:

        cursor.close()


    # =====================================================
    # RENDER ADMIN DASHBOARD
    # =====================================================

    return render_template(

        "admin_dashboard.html",

        total_users=total_users,

        active_users=active_users,

        inactive_users=inactive_users,

        total_products=total_products,

        users_by_role=users_by_role

    )