import sys
import os
import io


from flask import (
    Flask,
    redirect,
    url_for,
    send_file,
    request,
    jsonify
)


from flask_login import (
    LoginManager,
    login_required,
    current_user,
    UserMixin
)


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# =========================================================
# PATH CONFIGURATION
# =========================================================

current_dir = os.path.dirname(
    os.path.abspath(__file__)
)


parent_dir = os.path.dirname(
    current_dir
)


sys.path.insert(
    0,
    parent_dir
)


sys.path.insert(
    0,
    current_dir
)


# =========================================================
# IMPORTS
# =========================================================

from config import Config


from database.connection import (
    init_db,
    mysql
)


from routes.auth import auth_bp
from routes.products import products_bp
from routes.fuel import fuel_bp
from routes.sales import sales_bp
from routes.reports import reports_bp
from routes.admin import admin_bp
from routes.users import users_bp
from routes.api_auth import api_auth_bp
from routes.api_products import api_products_bp
from routes.api_fuel import api_fuel_bp
from routes.api_sales import api_sales_bp
from routes.api_reports import api_reports_bp
from routes.api_admin import api_admin_bp
from routes.api_users import api_users_bp


# =========================================================
# FRONTEND PATH
# =========================================================

base_dir = (

    parent_dir

    if os.path.exists(

        os.path.join(
            parent_dir,
            "frontend"
        )

    )

    else current_dir

)


template_folder = os.path.join(

    base_dir,
    "frontend",
    "templates"

)


static_folder = os.path.join(

    base_dir,
    "frontend"

)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(

    __name__,

    template_folder=template_folder,

    static_folder=static_folder,

    static_url_path=""

)


app.config.from_object(
    Config
)


# =========================================================
# DATABASE
# =========================================================

init_db(
    app
)


# =========================================================
# USER MODEL FOR FLASK-LOGIN
# =========================================================

class User(UserMixin):


    def __init__(
        self,
        user_id,
        username,
        role,
        full_name=""
    ):


        self.id = user_id

        self.username = username

        self.role = role

        self.full_name = full_name


# =========================================================
# LOGIN MANAGER
# =========================================================

login_manager = LoginManager()


login_manager.init_app(
    app
)


login_manager.login_view = (
    "auth.login"
)


# =========================================================
# LOAD USER
# =========================================================

@login_manager.user_loader
def load_user(user_id):


    cursor = None


    try:


        cursor = mysql.connection.cursor()


        cursor.execute(

            """

            SELECT

                user_id,

                username,

                role,

                full_name


            FROM users


            WHERE

                user_id = %s

                AND is_active = 1

            """,

            (
                user_id,
            )

        )


        user_data = cursor.fetchone()


        if user_data:


            # Supports DictCursor
            if isinstance(
                user_data,
                dict
            ):


                return User(

                    user_data["user_id"],

                    user_data["username"],

                    user_data["role"],

                    user_data.get(
                        "full_name",
                        ""
                    )

                )


            # Supports normal tuple cursor
            return User(

                user_data[0],

                user_data[1],

                user_data[2],

                user_data[3]
                if len(user_data) > 3
                else ""

            )


    except Exception as error:


        print(
            "User loader error:",
            error
        )


    finally:


        if cursor:

            cursor.close()


    return None


# =========================================================
# REGISTER BLUEPRINTS
# =========================================================

app.register_blueprint(

    auth_bp,

    url_prefix="/auth"

)

# =========================================================
# API BLUEPRINTS
# =========================================================

# =========================================================
# API BLUEPRINTS
# =========================================================

app.register_blueprint(
    api_auth_bp,
    url_prefix="/api/auth"
)

app.register_blueprint(
    api_products_bp,
    url_prefix="/api/products"
)

app.register_blueprint(
    api_fuel_bp,
    url_prefix="/api/fuel"
)

app.register_blueprint(
    api_sales_bp,
    url_prefix="/api/sales"
)

app.register_blueprint(
    api_reports_bp,
    url_prefix="/api/reports"
)

app.register_blueprint(
    api_admin_bp,
    url_prefix="/api/admin"
)

app.register_blueprint(
    api_users_bp,
    url_prefix="/api/users"
)


app.register_blueprint(

    products_bp

)


app.register_blueprint(

    fuel_bp

)


app.register_blueprint(

    sales_bp

)


app.register_blueprint(

    reports_bp

)

app.register_blueprint(admin_bp)

app.register_blueprint(users_bp)


# =========================================================
# LOW STOCK NOTIFICATIONS
# =========================================================

@app.context_processor
def inject_notifications():


    if not current_user.is_authenticated:


        return dict(

            low_stock_alerts=[]

        )


    cursor = None


    try:


        cursor = mysql.connection.cursor()


        cursor.execute(

            """

            SELECT

                p.product_id,

                p.product_name,

                c.category_name,

                i.stock_quantity,

                p.low_stock_threshold


            FROM inventory i


            JOIN products p

                ON i.product_id = p.product_id


            JOIN categories c

                ON p.category_id = c.category_id


            WHERE

                i.stock_quantity
                    <= p.low_stock_threshold

                AND p.is_active = 1


            ORDER BY

                i.stock_quantity ASC

            """

        )


        alerts = cursor.fetchall()


        return dict(

            low_stock_alerts=alerts

        )


    except Exception as error:


        print(

            "Notification error:",
            error

        )


        return dict(

            low_stock_alerts=[]

        )


    finally:


        if cursor:

            cursor.close()


# =========================================================
# PDF EXPORT
# =========================================================

@app.route(
    "/export-pdf"
)


@login_required
def export_pdf():


    # =====================================================
    # MANAGER / ADMIN ONLY
    # =====================================================

    if current_user.role not in (

        "manager",

        "admin"

    ):


        return (

            "Unauthorized Access",

            403

        )


    # =====================================================
    # DATE FILTER
    # =====================================================

    start_date = request.args.get(

        "start_date",

        "2026-01-01"

    )


    end_date = request.args.get(

        "end_date",

        "2026-12-31"

    )


    rows = []


    cursor = mysql.connection.cursor()


    try:


        # =================================================
        # STORE SALES AND PROFIT REPORT
        #
        # Profit uses products.cost_price
        # because sale_items does NOT have cost_price.
        # =================================================

        cursor.execute(

            """

            SELECT

                p.product_name,

                c.category_name,


                COALESCE(
                    SUM(si.quantity),
                    0
                ) AS qty,


                COALESCE(
                    SUM(si.subtotal),
                    0
                ) AS revenue,


                COALESCE(

                    SUM(

                        (
                            si.unit_price
                            - p.cost_price
                        )

                        * si.quantity

                    ),

                    0

                ) AS profit


            FROM sale_items si


            JOIN sales s

                ON si.sale_id = s.sale_id


            JOIN products p

                ON si.product_id = p.product_id


            JOIN categories c

                ON p.category_id = c.category_id


            WHERE

                DATE(s.sale_date)
                    BETWEEN %s AND %s

                AND s.status = 'completed'

                AND s.sale_type = 'store'


            GROUP BY

                p.product_id,

                p.product_name,

                c.category_name


            ORDER BY

                qty DESC

            """,

            (

                start_date,

                end_date

            )

        )


        rows = cursor.fetchall()


    except Exception as error:


        print(

            f"Error generating PDF report: {error}"

        )


        rows = []


    finally:


        cursor.close()


    # =====================================================
    # CREATE PDF BUFFER
    # =====================================================

    buffer = io.BytesIO()


    pdf = canvas.Canvas(

        buffer,

        pagesize=letter

    )


    pdf.setTitle(

        "GAZZ POS Sales Report"

    )


    # =====================================================
    # TITLE
    # =====================================================

    pdf.setFont(

        "Helvetica-Bold",

        16

    )


    pdf.drawString(

        40,

        750,

        "GAZZ POS - Sales & Profit Report"

    )


    pdf.setFont(

        "Helvetica",

        10

    )


    pdf.drawString(

        40,

        735,

        f"Date Range: {start_date} to {end_date}"

    )


    # =====================================================
    # TABLE HEADER
    # =====================================================

    y = 690


    pdf.setFont(

        "Helvetica-Bold",

        10

    )


    pdf.drawString(

        40,

        y,

        "Product"

    )


    pdf.drawString(

        200,

        y,

        "Category"

    )


    pdf.drawString(

        300,

        y,

        "Qty Sold"

    )


    pdf.drawString(

        380,

        y,

        "Revenue"

    )


    pdf.drawString(

        480,

        y,

        "Profit"

    )


    pdf.line(

        40,

        y - 5,

        550,

        y - 5

    )


    # =====================================================
    # TABLE CONTENT
    # =====================================================

    pdf.setFont(

        "Helvetica",

        10

    )


    y -= 25


    for row in rows:


        # Supports DictCursor
        if isinstance(
            row,
            dict
        ):


            name = row["product_name"]

            category = row["category_name"]

            quantity = row["qty"]

            revenue = row["revenue"]

            profit = row["profit"]


        # Supports normal tuple cursor
        else:


            name = row[0]

            category = row[1]

            quantity = row[2]

            revenue = row[3]

            profit = row[4]


        pdf.drawString(

            40,

            y,

            str(name)[:22]

        )


        pdf.drawString(

            200,

            y,

            str(category)[:15]

        )


        pdf.drawString(

            300,

            y,

            str(quantity)

        )


        pdf.drawString(

            380,

            y,

            f"P{float(revenue or 0):.2f}"

        )


        pdf.drawString(

            480,

            y,

            f"P{float(profit or 0):.2f}"

        )


        y -= 20


        # =================================================
        # NEW PAGE
        # =================================================

        if y < 50:


            pdf.showPage()


            y = 750


            # Repeat header

            pdf.setFont(

                "Helvetica-Bold",

                10

            )


            pdf.drawString(

                40,

                y,

                "Product"

            )


            pdf.drawString(

                200,

                y,

                "Category"

            )


            pdf.drawString(

                300,

                y,

                "Qty Sold"

            )


            pdf.drawString(

                380,

                y,

                "Revenue"

            )


            pdf.drawString(

                480,

                y,

                "Profit"

            )


            pdf.line(

                40,

                y - 5,

                550,

                y - 5

            )


            pdf.setFont(

                "Helvetica",

                10

            )


            y -= 25


    # =====================================================
    # SAVE PDF
    # =====================================================

    pdf.save()


    buffer.seek(
        0
    )


    return send_file(

        buffer,

        as_attachment=True,

        download_name="GAZZ_POS_Report.pdf",

        mimetype="application/pdf"

    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():


    return redirect(

        url_for(

            "auth.login"

        )

    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":


    app.run(

        debug=True

    )
