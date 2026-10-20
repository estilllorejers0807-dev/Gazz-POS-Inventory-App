from flask import Blueprint, render_template, request, redirect, url_for, flash

from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

import bcrypt
import os

from database.connection import mysql


# =========================================================
# TEMPLATE DIRECTORY
# =========================================================

TEMPLATE_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    ),
    "frontend",
    "templates"
)


# =========================================================
# BLUEPRINT
# =========================================================

auth_bp = Blueprint(
    "auth",
    __name__,
    template_folder=TEMPLATE_DIR
)


# =========================================================
# REDIRECT BY ROLE
# =========================================================

def redirect_by_role(role):
    """
    Redirect users based on their assigned role.
    """

    # Manager and Admin
    if role in ("manager"):

        return redirect(
            url_for("reports.manager_analytics")
        )

    if role == "admin":

        return redirect(
            url_for("admin.admin_dashboard")
        )

    # Fuel Cashier / Attendant
    elif role in ("fuel_cashier", "attendant"):

        return redirect(
            url_for("sales.fuel_pos")
        )


    # Store Cashier
    elif role in ("store_cashier", "cashier"):

        return redirect(
            url_for("sales.convenience_pos")
        )


    # Default
    return redirect(
        url_for("sales.convenience_pos")
    )


# =========================================================
# LOGIN
# =========================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    # Already logged in
    if current_user.is_authenticated:

        return redirect_by_role(
            current_user.role
        )


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()


        password = request.form.get(
            "password",
            ""
        )


        # Validation
        if not username or not password:

            flash(
                "Username and password are required.",
                "error"
            )

            return render_template(
                "login.html"
            )


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
                WHERE username = %s
                AND is_active = 1
                """,
                (username,)
            )


            user_data = cursor.fetchone()


        finally:

            cursor.close()


        # Check user
        if user_data:

            stored_hash = user_data[
                "password_hash"
            ]


            # Check password
            if bcrypt.checkpw(

                password.encode("utf-8"),

                stored_hash.encode("utf-8")

            ):


                from app import User


                user = User(

                    user_data["user_id"],

                    user_data["username"],

                    user_data["role"],

                    user_data["full_name"]

                )


                login_user(user)



                return redirect_by_role(
                    user.role
                )


        # Invalid credentials
        flash(
            "Invalid username or password.",
            "error"
        )


    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# =========================================================
# SIGNUP
# =========================================================

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        # =============================================
        # GET FORM DATA
        # =============================================

        username = request.form.get(
            "username",
            ""
        ).strip()


        password = request.form.get(
            "password",
            ""
        )


        full_name = request.form.get(
            "full_name",
            ""
        ).strip()


        role = request.form.get(
            "role",
            "store_cashier"
        ).strip()


        # =============================================
        # VALIDATION
        # =============================================

        if not username or not password or not full_name:

            flash(
                "Username, password, and full name "
                "are required.",
                "error"
            )

            return render_template(
                "signup.html"
            )


        # Password length
        if len(password) < 6:

            flash(
                "Password must contain at least "
                "6 characters.",
                "error"
            )

            return render_template(
                "signup.html"
            )


        # =============================================
        # ALLOWED ROLES
        # =============================================

        allowed_roles = [

            "admin",

            "manager",

            "store_cashier",

            "fuel_cashier",

            "attendant"

        ]


        # Invalid role protection
        if role not in allowed_roles:

            role = "store_cashier"


        cursor = mysql.connection.cursor()


        try:

            # =========================================
            # CHECK DUPLICATE USERNAME
            # =========================================

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE username = %s
                """,
                (username,)
            )


            existing_user = cursor.fetchone()


            if existing_user:

                flash(
                    "Username already taken. "
                    "Please choose another.",
                    "error"
                )

                return render_template(
                    "signup.html"
                )


            # =========================================
            # HASH PASSWORD
            # =========================================

            hashed_pw = bcrypt.hashpw(

                password.encode("utf-8"),

                bcrypt.gensalt()

            ).decode("utf-8")


            # =========================================
            # INSERT USER
            # =========================================

            cursor.execute(
                """
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
                """,
                (

                    username,

                    hashed_pw,

                    full_name,

                    role

                )
            )


            # Save
            mysql.connection.commit()


            flash(
                "Account created successfully! "
                "Please log in.",
                "success"
            )


            return redirect(
                url_for("auth.login")
            )


        except Exception as error:

            mysql.connection.rollback()


            flash(
                f"Error creating account: {error}",
                "error"
            )


        finally:

            cursor.close()


    return render_template(
        "signup.html"
    )