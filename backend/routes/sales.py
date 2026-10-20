from decimal import Decimal, InvalidOperation

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

from database.connection import mysql

from utils.decorators import (
    store_access_required,
    fuel_access_required
)


sales_bp = Blueprint("sales", __name__)


# =========================================================
# HELPER FUNCTION
# =========================================================

def get_value(row, key, index=0):
    """
    Supports both DictCursor and normal tuple cursor.
    """

    if isinstance(row, dict):
        return row.get(key)

    return row[index]


# =========================================================
# CONVENIENCE STORE POS
# =========================================================

@sales_bp.route("/convenience_pos", methods=["GET", "POST"])
@login_required
@store_access_required
def convenience_pos():

    # =====================================================
    # PROCESS STORE SALE
    # =====================================================

    if request.method == "POST":

        product_id_value = request.form.get(
            "product_id",
            ""
        ).strip()

        customer_id_value = request.form.get(
            "customer_id",
            ""
        ).strip()

        quantity_value = request.form.get(
            "quantity",
            "1"
        ).strip()

        amount_paid_value = request.form.get(
            "amount_paid",
            "0"
        ).strip()

        try:

            product_id = int(product_id_value)

            customer_id = (
                int(customer_id_value)
                if customer_id_value
                else None
            )

            quantity = int(quantity_value)

            amount_received = Decimal(
                amount_paid_value
            )

        except (
            ValueError,
            InvalidOperation
        ):

            flash(
                "Please enter valid sale details.",
                "error"
            )

            return redirect(
                url_for("sales.convenience_pos")
            )


        # =================================================
        # VALIDATE QUANTITY
        # =================================================

        if quantity <= 0:

            flash(
                "Quantity must be greater than zero.",
                "error"
            )

            return redirect(
                url_for("sales.convenience_pos")
            )


        if amount_received < 0:

            flash(
                "Amount paid cannot be negative.",
                "error"
            )

            return redirect(
                url_for("sales.convenience_pos")
            )


        cursor = mysql.connection.cursor()

        try:

            # =============================================
            # GET PRODUCT AND LOCK INVENTORY
            #
            # cost_price REMOVED because it does not exist
            # in your products table.
            # =============================================

            cursor.execute("""
                SELECT
                    p.product_id,
                    p.product_name,
                    p.selling_price,
                    i.stock_quantity

                FROM products p

                JOIN inventory i
                    ON p.product_id = i.product_id

                WHERE
                    p.product_id = %s
                    AND p.is_active = 1

                FOR UPDATE
            """, (
                product_id,
            ))

            product = cursor.fetchone()


            # =============================================
            # CHECK PRODUCT
            # =============================================

            if not product:

                flash(
                    "Product was not found.",
                    "error"
                )

                return redirect(
                    url_for(
                        "sales.convenience_pos"
                    )
                )


            # =============================================
            # GET PRODUCT DATA
            # =============================================

            product_name = get_value(
                product,
                "product_name",
                1
            )


            selling_price = Decimal(
                str(
                    get_value(
                        product,
                        "selling_price",
                        2
                    )
                )
            )


            stock_quantity = int(
                get_value(
                    product,
                    "stock_quantity",
                    3
                )
            )


            # =============================================
            # CHECK AVAILABLE STOCK
            # =============================================

            if stock_quantity < quantity:

                flash(
                    f"Insufficient stock. "
                    f"Only {stock_quantity} available.",
                    "error"
                )

                return redirect(
                    url_for(
                        "sales.convenience_pos"
                    )
                )


            # =============================================
            # CALCULATE AMOUNTS
            # =============================================

            subtotal = (
                selling_price
                * quantity
            )

            total_amount = subtotal


            # =============================================
            # VALIDATE PAYMENT
            # =============================================

            if amount_received < total_amount:

                flash(
                    "Amount paid is less than the total amount.",
                    "error"
                )

                return redirect(
                    url_for(
                        "sales.convenience_pos"
                    )
                )


            change_amount = (
                amount_received
                - total_amount
            )


            # =============================================
            # CREATE MAIN SALE
            # =============================================

            cursor.execute("""
                INSERT INTO sales
                (
                    user_id,
                    sale_type,
                    subtotal,
                    total_amount,
                    payment_type,
                    amount_received,
                    change_amount,
                    status,
                    customer_id
                )

                VALUES
                (
                    %s,
                    'store',
                    %s,
                    %s,
                    'cash',
                    %s,
                    %s,
                    'completed',
                    %s
                )
            """, (
                current_user.id,
                subtotal,
                total_amount,
                amount_received,
                change_amount,
                customer_id
            ))


            sale_id = cursor.lastrowid


            # =============================================
            # CREATE SALE ITEM
            #
            # cost_price REMOVED
            # =============================================

            cursor.execute("""
                INSERT INTO sale_items
                (
                    sale_id,
                    product_id,
                    quantity,
                    unit_price,
                    subtotal
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                sale_id,
                product_id,
                quantity,
                selling_price,
                subtotal
            ))


            # =============================================
            # UPDATE INVENTORY
            # =============================================

            new_stock = (
                stock_quantity
                - quantity
            )


            cursor.execute("""
                UPDATE inventory

                SET stock_quantity = %s

                WHERE product_id = %s
            """, (
                new_stock,
                product_id
            ))


            # =============================================
            # RECORD INVENTORY MOVEMENT
            # =============================================

            cursor.execute("""
                INSERT INTO inventory_movements
                (
                    product_id,
                    user_id,
                    movement_type,
                    quantity,
                    previous_quantity,
                    new_quantity,
                    reason
                )

                VALUES
                (
                    %s,
                    %s,
                    'stock_out',
                    %s,
                    %s,
                    %s,
                    %s
                )
            """, (
                product_id,
                current_user.id,
                quantity,
                stock_quantity,
                new_stock,
                f"Sold through POS - Sale #{sale_id}"
            ))


            # =============================================
            # COMMIT TRANSACTION
            # =============================================

            mysql.connection.commit()


            flash(
                f"Sale completed successfully! "
                f"Change: ₱{change_amount:.2f}",
                "success"
            )


            return redirect(
                url_for(
                    "sales.store_receipt",
                    sale_id=sale_id
                )
            )


        except Exception as error:

            mysql.connection.rollback()


            flash(
                f"Could not complete sale: {error}",
                "error"
            )


            return redirect(
                url_for(
                    "sales.convenience_pos"
                )
            )


        finally:

            cursor.close()


    # =====================================================
    # LOAD STORE POS DATA
    # =====================================================

    cursor = mysql.connection.cursor()

    try:

        # =============================================
        # PRODUCTS WITH AVAILABLE STOCK
        # =============================================

        cursor.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.selling_price,
                p.unit,

                COALESCE(
                    i.stock_quantity,
                    0
                ) AS stock_quantity

            FROM products p

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.is_active = 1

                AND COALESCE(
                    i.stock_quantity,
                    0
                ) > 0

            ORDER BY
                p.product_name
        """)

        items = cursor.fetchall()


        # =============================================
        # CUSTOMERS
        # =============================================

        cursor.execute("""
            SELECT
                customer_id,
                name,
                phone

            FROM customers

            ORDER BY name
        """)

        customers = cursor.fetchall()


    except Exception as error:

        flash(
            f"Could not load POS data: {error}",
            "error"
        )

        items = []
        customers = []


    finally:

        cursor.close()


    return render_template(
        "convenience_pos.html",
        items=items,
        customers=customers
    )


# =========================================================
# FUEL POS PAGE
# =========================================================

@sales_bp.route("/fuel_pos")
@login_required
@fuel_access_required
def fuel_pos():

    cursor = mysql.connection.cursor()

    try:

        # =============================================
        # CUSTOMERS
        # =============================================

        cursor.execute("""
            SELECT
                customer_id,
                name,
                phone

            FROM customers

            ORDER BY name
        """)

        customers = cursor.fetchall()


        # =============================================
        # FUEL PUMPS WITH THEIR ASSIGNED FUEL TYPE
        # =============================================

        cursor.execute("""
            SELECT
                p.pump_id,
                p.pump_number,
                p.fuel_type_id,
                f.fuel_name,
                f.price_per_liter

            FROM fuel_pumps p

            JOIN fuel_types f
                ON p.fuel_type_id = f.fuel_type_id

            WHERE
                p.is_active = 1
                AND f.is_active = 1

            ORDER BY p.pump_number
        """)

        pumps = cursor.fetchall()


    except Exception as error:

        flash(
            f"Could not load fuel POS data: {error}",
            "error"
        )

        customers = []
        pumps = []


    finally:

        cursor.close()


    return render_template(
        "fuel_pos.html",
        customers=customers,
        pumps=pumps
    )


# =========================================================
# COMPLETE FUEL SALE
# =========================================================

@sales_bp.route(
    "/fuel_pos/complete",
    methods=["POST"]
)
@login_required
@fuel_access_required
def complete_fuel_sale():

    try:

        # =============================================
        # GET FORM DATA
        # =============================================

        customer_id_value = request.form.get(
            "customer_id",
            ""
        ).strip()


        pump_id = int(
            request.form.get(
                "pump_id",
                ""
            )
        )


        liters = Decimal(
            request.form.get(
                "liters",
                "0"
            )
        )


        payment_type = request.form.get(
            "payment_type",
            "cash"
        ).strip()


        amount_received = Decimal(
            request.form.get(
                "amount_received",
                "0"
            )
        )


        customer_id = (
            int(customer_id_value)
            if customer_id_value
            else None
        )


    except (
        ValueError,
        InvalidOperation
    ):

        flash(
            "Please enter valid fuel sale details.",
            "error"
        )

        return redirect(
            url_for(
                "sales.fuel_pos"
            )
        )


    # =====================================================
    # VALIDATE LITERS
    # =====================================================

    if liters <= 0:

        flash(
            "Liters must be greater than zero.",
            "error"
        )

        return redirect(
            url_for(
                "sales.fuel_pos"
            )
        )


    # =====================================================
    # VALIDATE PAYMENT METHOD
    # =====================================================

    allowed_payments = (
        "cash",
        "gcash",
        "other"
    )


    if payment_type not in allowed_payments:

        payment_type = "cash"


    cursor = mysql.connection.cursor()


    try:

        # =============================================
        # GET PUMP AND ITS ASSIGNED FUEL TYPE
        # =============================================

        cursor.execute("""
            SELECT
                p.pump_id,
                p.pump_number,
                p.fuel_type_id,
                f.fuel_name,
                f.price_per_liter

            FROM fuel_pumps p

            JOIN fuel_types f
                ON p.fuel_type_id = f.fuel_type_id

            WHERE
                p.pump_id = %s
                AND p.is_active = 1
                AND f.is_active = 1

            FOR UPDATE
        """, (
            pump_id,
        ))


        pump = cursor.fetchone()


        # =============================================
        # CHECK PUMP
        # =============================================

        if not pump:

            flash(
                "Selected fuel pump is not available.",
                "error"
            )

            return redirect(
                url_for(
                    "sales.fuel_pos"
                )
            )


        # =============================================
        # GET FUEL INFORMATION FROM PUMP
        # =============================================

        fuel_type_id = get_value(
            pump,
            "fuel_type_id",
            2
        )


        fuel_name = get_value(
            pump,
            "fuel_name",
            3
        )


        price_per_liter = Decimal(
            str(
                get_value(
                    pump,
                    "price_per_liter",
                    4
                )
            )
        )


        # =============================================
        # CALCULATE TOTAL
        # =============================================

        total_amount = (
            liters
            * price_per_liter
        )


        # =============================================
        # PAYMENT VALIDATION
        # =============================================

        if payment_type == "cash":

            if amount_received < total_amount:

                flash(
                    "Cash received is less than "
                    "the total amount.",
                    "error"
                )

                return redirect(
                    url_for(
                        "sales.fuel_pos"
                    )
                )


            change_amount = (
                amount_received
                - total_amount
            )


        else:

            amount_received = total_amount

            change_amount = Decimal(
                "0.00"
            )


        # =============================================
        # CREATE MAIN SALE
        # =============================================

        cursor.execute("""
            INSERT INTO sales
            (
                user_id,
                sale_type,
                subtotal,
                total_amount,
                payment_type,
                amount_received,
                change_amount,
                status,
                customer_id
            )

            VALUES
            (
                %s,
                'fuel',
                %s,
                %s,
                %s,
                %s,
                %s,
                'completed',
                %s
            )
        """, (
            current_user.id,
            total_amount,
            total_amount,
            payment_type,
            amount_received,
            change_amount,
            customer_id
        ))


        sale_id = cursor.lastrowid


        # =============================================
        # CREATE FUEL SALE RECORD
        # =============================================

        cursor.execute("""
            INSERT INTO fuel_sales
            (
                sale_id,
                pump_id,
                fuel_type_id,
                liters,
                price_per_liter,
                total_amount
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            sale_id,
            pump_id,
            fuel_type_id,
            liters,
            price_per_liter,
            total_amount
        ))


        # =============================================
        # COMMIT TRANSACTION
        # =============================================

        mysql.connection.commit()


        flash(
            f"Fuel sale completed successfully! "
            f"Change: ₱{change_amount:.2f}",
            "success"
        )


        return redirect(
            url_for(
                "sales.fuel_receipt",
                sale_id=sale_id
            )
        )


    except Exception as error:

        mysql.connection.rollback()


        flash(
            f"Could not complete fuel sale: {error}",
            "error"
        )


        return redirect(
            url_for(
                "sales.fuel_pos"
            )
        )


    finally:

        cursor.close()


# =========================================================
# STORE RECEIPT
# =========================================================

@sales_bp.route(
    "/receipt/store/<int:sale_id>"
)
@login_required
@store_access_required
def store_receipt(sale_id):

    cursor = mysql.connection.cursor()

    try:

        # =============================================
        # GET MAIN SALE INFORMATION
        # =============================================

        cursor.execute("""
            SELECT
                s.sale_id,
                s.sale_date,
                s.subtotal,
                s.total_amount,
                s.payment_type,
                s.amount_received,
                s.change_amount,

                u.full_name,

                c.name AS customer_name

            FROM sales s

            JOIN users u
                ON s.user_id = u.user_id

            LEFT JOIN customers c
                ON s.customer_id = c.customer_id

            WHERE
                s.sale_id = %s
                AND s.sale_type = 'store'
        """, (
            sale_id,
        ))

        sale = cursor.fetchone()


        # =============================================
        # GET SALE ITEMS
        # =============================================

        cursor.execute("""
            SELECT
                p.product_name,
                si.quantity,
                si.unit_price,
                si.subtotal

            FROM sale_items si

            JOIN products p
                ON si.product_id = p.product_id

            WHERE
                si.sale_id = %s

            ORDER BY
                si.sale_item_id
        """, (
            sale_id,
        ))

        sale_items = cursor.fetchall()


    finally:

        cursor.close()


    # =============================================
    # CHECK RECEIPT
    # =============================================

    if not sale:

        flash(
            "Receipt not found.",
            "error"
        )

        return redirect(
            url_for(
                "sales.convenience_pos"
            )
        )


    return render_template(
        "store_receipt.html",
        sale=sale,
        sale_items=sale_items
    )


# =========================================================
# FUEL RECEIPT
# =========================================================

@sales_bp.route(
    "/receipt/fuel/<int:sale_id>"
)
@login_required
@fuel_access_required
def fuel_receipt(sale_id):

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT

                s.sale_id,
                s.sale_date,
                s.subtotal,
                s.total_amount,
                s.payment_type,
                s.amount_received,
                s.change_amount,

                u.full_name,

                c.name AS customer_name,

                fs.liters,
                fs.price_per_liter,

                fs.total_amount
                    AS fuel_total,

                fp.pump_number,

                ft.fuel_name

            FROM sales s

            JOIN users u
                ON s.user_id = u.user_id

            LEFT JOIN customers c
                ON s.customer_id = c.customer_id

            JOIN fuel_sales fs
                ON s.sale_id = fs.sale_id

            JOIN fuel_pumps fp
                ON fs.pump_id = fp.pump_id

            JOIN fuel_types ft
                ON fs.fuel_type_id = ft.fuel_type_id

            WHERE
                s.sale_id = %s
                AND s.sale_type = 'fuel'

        """, (
            sale_id,
        ))

        sale = cursor.fetchone()


    finally:

        cursor.close()


    # =============================================
    # CHECK RECEIPT
    # =============================================

    if not sale:

        flash(
            "Receipt not found.",
            "error"
        )

        return redirect(
            url_for(
                "sales.fuel_pos"
            )
        )


    return render_template(
        "fuel_receipt.html",
        sale=sale
    )