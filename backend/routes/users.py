from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)

import bcrypt

from database.connection import mysql


# =========================================================
# USERS BLUEPRINT
# =========================================================

users_bp = Blueprint(
    "users",
    __name__
)


# =========================================================
# ADMIN ACCESS CHECK
# =========================================================

def admin_required():

    if current_user.role != "admin":

        return False

    return True


# =========================================================
# USER MANAGEMENT
# =========================================================

@users_bp.route("/admin/users")
@login_required
def users():

    # =====================================================
    # ADMIN ONLY
    # =====================================================

    if not admin_required():

        return (
            "Access Denied: Administrator access required.",
            403
        )


    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # GET ALL USERS
        # =================================================

        cursor.execute("""
            SELECT user_id, username, full_name, role, is_active
            FROM users
            ORDER BY user_id ASC
        """)

        users_data = cursor.fetchall()


        # =================================================
        # USER COUNTS
        # =================================================

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

        user_summary = cursor.fetchone()


    except Exception as error:

        print(
            f"User Management SQL Error: {error}"
        )

        users_data = []

        user_summary = {
            "total_users": 0,
            "active_users": 0,
            "inactive_users": 0
        }

        flash(
            "Could not load user accounts.",
            "error"
        )


    finally:

        cursor.close()


    return render_template(
        "users.html",

        users=users_data,

        user_summary=user_summary
    )


# =========================================================
# ADD USER
# =========================================================

@users_bp.route(
    "/admin/users/add",
    methods=["POST"]
)
@login_required
def add_user():

    # =====================================================
    # ADMIN ONLY
    # =====================================================

    if not admin_required():

        return (
            "Access Denied: Administrator access required.",
            403
        )


    # =====================================================
    # GET FORM DATA
    # =====================================================

    username = request.form.get(
        "username",
        ""
    ).strip()


    full_name = request.form.get(
        "full_name",
        ""
    ).strip()


    password = request.form.get(
        "password",
        ""
    )


    role = request.form.get(
        "role",
        "store_cashier"
    ).strip()


    # =====================================================
    # VALIDATE
    # =====================================================

    if not username or not full_name or not password:

        flash(
            "Username, full name, and password are required.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    if len(password) < 6:

        flash(
            "Password must contain at least 6 characters.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    # =====================================================
    # ALLOWED ROLES
    # =====================================================

    allowed_roles = (
        "admin",
        "manager",
        "store_cashier",
        "fuel_cashier",
        "attendant"
    )


    if role not in allowed_roles:

        flash(
            "Invalid user role selected.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    cursor = mysql.connection.cursor()


    try:

        # =================================================
        # CHECK DUPLICATE USERNAME
        # =================================================

        cursor.execute("""
            SELECT
                user_id
            FROM users
            WHERE username = %s
        """, (
            username,
        ))

        existing_user = cursor.fetchone()


        if existing_user:

            flash(
                "Username already exists.",
                "error"
            )

            return redirect(
                url_for("users.users")
            )


        # =================================================
        # HASH PASSWORD
        # =================================================

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")


        # =================================================
        # INSERT USER
        # =================================================

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


        mysql.connection.commit()


        flash(
            "User account created successfully.",
            "success"
        )


    except Exception as error:

        mysql.connection.rollback()

        print(
            f"Add User SQL Error: {error}"
        )

        flash(
            f"Could not create user: {error}",
            "error"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("users.users")
    )


# =========================================================
# EDIT USER
# =========================================================

@users_bp.route(
    "/admin/users/<int:user_id>/edit",
    methods=["POST"]
)
@login_required
def edit_user(user_id):

    # =====================================================
    # ADMIN ONLY
    # =====================================================

    if not admin_required():

        return (
            "Access Denied: Administrator access required.",
            403
        )


    # =====================================================
    # GET FORM DATA
    # =====================================================

    username = request.form.get(
        "username",
        ""
    ).strip()


    full_name = request.form.get(
        "full_name",
        ""
    ).strip()


    role = request.form.get(
        "role",
        ""
    ).strip()


    # =====================================================
    # VALIDATION
    # =====================================================

    if not username or not full_name or not role:

        flash(
            "Username, full name, and role are required.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    allowed_roles = (
        "admin",
        "manager",
        "store_cashier",
        "fuel_cashier",
        "attendant"
    )


    if role not in allowed_roles:

        flash(
            "Invalid user role.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    cursor = mysql.connection.cursor()


    try:

        # =================================================
        # CHECK USER EXISTS
        # =================================================

        cursor.execute("""
            SELECT
                user_id
            FROM users
            WHERE user_id = %s
        """, (
            user_id,
        ))

        target_user = cursor.fetchone()


        if not target_user:

            flash(
                "User account was not found.",
                "error"
            )

            return redirect(
                url_for("users.users")
            )


        # =================================================
        # CHECK DUPLICATE USERNAME
        # =================================================

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

        duplicate_user = cursor.fetchone()


        if duplicate_user:

            flash(
                "Username is already being used by another account.",
                "error"
            )

            return redirect(
                url_for("users.users")
            )


        # =================================================
        # UPDATE USER
        # =================================================

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


        flash(
            "User account updated successfully.",
            "success"
        )


    except Exception as error:

        mysql.connection.rollback()

        print(
            f"Edit User SQL Error: {error}"
        )

        flash(
            f"Could not update user: {error}",
            "error"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("users.users")
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@users_bp.route(
    "/admin/users/<int:user_id>/password",
    methods=["POST"]
)
@login_required
def change_password(user_id):

    # =====================================================
    # ADMIN ONLY
    # =====================================================

    if not admin_required():

        return (
            "Access Denied: Administrator access required.",
            403
        )


    password = request.form.get(
        "password",
        ""
    )


    if not password:

        flash(
            "Password is required.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    if len(password) < 6:

        flash(
            "Password must contain at least 6 characters.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    cursor = mysql.connection.cursor()


    try:

        # =================================================
        # CHECK USER
        # =================================================

        cursor.execute("""
            SELECT
                user_id
            FROM users
            WHERE user_id = %s
        """, (
            user_id,
        ))

        target_user = cursor.fetchone()


        if not target_user:

            flash(
                "User account was not found.",
                "error"
            )

            return redirect(
                url_for("users.users")
            )


        # =================================================
        # HASH NEW PASSWORD
        # =================================================

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")


        # =================================================
        # UPDATE PASSWORD
        # =================================================

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


        flash(
            "User password updated successfully.",
            "success"
        )


    except Exception as error:

        mysql.connection.rollback()

        print(
            f"Change Password SQL Error: {error}"
        )

        flash(
            f"Could not change password: {error}",
            "error"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("users.users")
    )


# =========================================================
# ACTIVATE USER
# =========================================================

@users_bp.route(
    "/admin/users/<int:user_id>/activate",
    methods=["POST"]
)
@login_required
def activate_user(user_id):

    # =====================================================
    # ADMIN ONLY
    # =====================================================

    if not admin_required():

        return (
            "Access Denied: Administrator access required.",
            403
        )


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

        target_user = cursor.fetchone()


        if not target_user:

            flash(
                "User account was not found.",
                "error"
            )

            return redirect(
                url_for("users.users")
            )


        cursor.execute("""
            UPDATE users
            SET is_active = 1
            WHERE user_id = %s
        """, (
            user_id,
        ))


        mysql.connection.commit()


        flash(
            "User account activated successfully.",
            "success"
        )


    except Exception as error:

        mysql.connection.rollback()

        print(
            f"Activate User SQL Error: {error}"
        )

        flash(
            f"Could not activate user: {error}",
            "error"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("users.users")
    )


# =========================================================
# DEACTIVATE USER
# =========================================================

@users_bp.route(
    "/admin/users/<int:user_id>/deactivate",
    methods=["POST"]
)
@login_required
def deactivate_user(user_id):

    # =====================================================
    # ADMIN ONLY
    # =====================================================

    if not admin_required():

        return (
            "Access Denied: Administrator access required.",
            403
        )


    # =====================================================
    # PREVENT SELF-DEACTIVATION
    # =====================================================

    if user_id == current_user.id:

        flash(
            "You cannot deactivate your own administrator account.",
            "error"
        )

        return redirect(
            url_for("users.users")
        )


    cursor = mysql.connection.cursor()


    try:

        # =================================================
        # CHECK USER
        # =================================================

        cursor.execute("""
            SELECT
                user_id,
                is_active
            FROM users
            WHERE user_id = %s
        """, (
            user_id,
        ))

        target_user = cursor.fetchone()


        if not target_user:

            flash(
                "User account was not found.",
                "error"
            )

            return redirect(
                url_for("users.users")
            )


        # =================================================
        # DEACTIVATE
        # =================================================

        cursor.execute("""
            UPDATE users
            SET is_active = 0
            WHERE user_id = %s
        """, (
            user_id,
        ))


        mysql.connection.commit()


        flash(
            "User account deactivated successfully.",
            "success"
        )


    except Exception as error:

        mysql.connection.rollback()

        print(
            f"Deactivate User SQL Error: {error}"
        )

        flash(
            f"Could not deactivate user: {error}",
            "error"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("users.users")
    )