from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    jsonify,
    request
)

from flask_login import current_user

from database.connection import mysql


api_sales_bp = Blueprint(
    "api_sales",
    __name__
)


# =========================================================
# ACCESS HELPERS
# =========================================================

def store_access():

    if not current_user.is_authenticated:
        return False

    return current_user.role in (
        "admin",
        "manager",
        "store_cashier",
        "cashier"
    )


def fuel_access():

    if not current_user.is_authenticated:
        return False

    return current_user.role in (
        "admin",
        "manager",
        "fuel_cashier",
        "attendant"
    )


def get_value(row, key, index=0):

    if isinstance(row, dict):
        return row.get(key)

    return row[index]


# =========================================================
# STORE PRODUCTS FOR POS
# GET /api/sales/store/products
# =========================================================

@api_sales_bp.route(
    "/store/products",
    methods=["GET"]
)
def store_products():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not store_access():

        return jsonify({
            "success": False,
            "message": "Store POS access required."
        }), 403

    cursor = mysql.connection.cursor()

    try:

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

        rows = cursor.fetchall()

        products = []

        for row in rows:

            products.append({
                "product_id":
                    row["product_id"],

                "product_name":
                    row["product_name"],

                "selling_price":
                    float(row["selling_price"] or 0),

                "unit":
                    row["unit"],

                "stock_quantity":
                    int(row["stock_quantity"] or 0)
            })

        return jsonify({
            "success": True,
            "products": products
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not load store products.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# STORE CUSTOMERS
# GET /api/sales/store/customers
# =========================================================

@api_sales_bp.route(
    "/store/customers",
    methods=["GET"]
)
def store_customers():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not store_access():

        return jsonify({
            "success": False,
            "message": "Store POS access required."
        }), 403

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                customer_id,
                name,
                phone

            FROM customers

            ORDER BY name
        """)

        rows = cursor.fetchall()

        customers = []

        for row in rows:

            customers.append({
                "customer_id":
                    row["customer_id"],

                "name":
                    row["name"],

                "phone":
                    row["phone"]
            })

        return jsonify({
            "success": True,
            "customers": customers
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not load customers.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# COMPLETE STORE SALE
# POST /api/sales/store
# =========================================================

@api_sales_bp.route(
    "/store",
    methods=["POST"]
)
def complete_store_sale():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not store_access():

        return jsonify({
            "success": False,
            "message": "Store POS access required."
        }), 403

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    try:

        product_id = int(
            data.get("product_id")
        )

        quantity = int(
            data.get(
                "quantity",
                1
            )
        )

        amount_received = Decimal(
            str(
                data.get(
                    "amount_paid",
                    0
                )
            )
        )

    except (
        ValueError,
        TypeError,
        InvalidOperation
    ):

        return jsonify({
            "success": False,
            "message": "Invalid sale details."
        }), 400

    customer_id_value = data.get(
        "customer_id"
    )

    try:

        customer_id = (
            int(customer_id_value)
            if customer_id_value
            else None
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": "Invalid customer ID."
        }), 400

    if quantity <= 0:

        return jsonify({
            "success": False,
            "message": "Quantity must be greater than zero."
        }), 400

    if amount_received < 0:

        return jsonify({
            "success": False,
            "message": "Amount paid cannot be negative."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # LOCK PRODUCT INVENTORY
        # =================================================

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

        if not product:

            return jsonify({
                "success": False,
                "message": "Product was not found."
            }), 404

        product_name = product[
            "product_name"
        ]

        selling_price = Decimal(
            str(
                product["selling_price"]
            )
        )

        stock_quantity = int(
            product["stock_quantity"]
        )

        if stock_quantity < quantity:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": (
                    "Insufficient stock. "
                    f"Only {stock_quantity} available."
                )
            }), 400

        subtotal = (
            selling_price
            * quantity
        )

        total_amount = subtotal

        if amount_received < total_amount:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": (
                    "Amount paid is less "
                    "than total amount."
                ),
                "total_amount": float(
                    total_amount
                )
            }), 400

        change_amount = (
            amount_received
            - total_amount
        )

        # =================================================
        # CREATE SALE
        # =================================================

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

        # =================================================
        # SALE ITEM
        # =================================================

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

        # =================================================
        # UPDATE INVENTORY
        # =================================================

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

        # =================================================
        # INVENTORY MOVEMENT
        # =================================================

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
            f"Sold through API POS - Sale #{sale_id}"
        ))

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Store sale completed.",
            "sale": {
                "sale_id": sale_id,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": float(
                    selling_price
                ),
                "subtotal": float(
                    subtotal
                ),
                "total_amount": float(
                    total_amount
                ),
                "amount_received": float(
                    amount_received
                ),
                "change_amount": float(
                    change_amount
                ),
                "remaining_stock": new_stock
            }
        }), 201

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not complete store sale.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# FUEL PUMPS
# GET /api/sales/fuel/pumps
# =========================================================

@api_sales_bp.route(
    "/fuel/pumps",
    methods=["GET"]
)
def fuel_pumps():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not fuel_access():

        return jsonify({
            "success": False,
            "message": "Fuel POS access required."
        }), 403

    cursor = mysql.connection.cursor()

    try:

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

        rows = cursor.fetchall()

        pumps = []

        for row in rows:

            pumps.append({
                "pump_id":
                    row["pump_id"],

                "pump_number":
                    row["pump_number"],

                "fuel_type_id":
                    row["fuel_type_id"],

                "fuel_name":
                    row["fuel_name"],

                "price_per_liter":
                    float(
                        row["price_per_liter"] or 0
                    )
            })

        return jsonify({
            "success": True,
            "pumps": pumps
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not load fuel pumps.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# COMPLETE FUEL SALE
# POST /api/sales/fuel
# =========================================================

@api_sales_bp.route(
    "/fuel",
    methods=["POST"]
)
def complete_fuel_sale():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not fuel_access():

        return jsonify({
            "success": False,
            "message": "Fuel POS access required."
        }), 403

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    try:

        pump_id = int(
            data.get("pump_id")
        )

        liters = Decimal(
            str(
                data.get("liters", 0)
            )
        )

        amount_received = Decimal(
            str(
                data.get(
                    "amount_received",
                    0
                )
            )
        )

    except (
        ValueError,
        TypeError,
        InvalidOperation
    ):

        return jsonify({
            "success": False,
            "message": "Invalid fuel sale details."
        }), 400

    customer_id_value = data.get(
        "customer_id"
    )

    try:

        customer_id = (
            int(customer_id_value)
            if customer_id_value
            else None
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": "Invalid customer ID."
        }), 400

    payment_type = data.get(
        "payment_type",
        "cash"
    ).strip().lower()

    if liters <= 0:

        return jsonify({
            "success": False,
            "message": "Liters must be greater than zero."
        }), 400

    if payment_type not in (
        "cash",
        "gcash",
        "other"
    ):

        payment_type = "cash"

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # GET PUMP
        # =================================================

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

        if not pump:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": "Fuel pump is not available."
            }), 404

        fuel_type_id = pump[
            "fuel_type_id"
        ]

        fuel_name = pump[
            "fuel_name"
        ]

        price_per_liter = Decimal(
            str(
                pump["price_per_liter"]
            )
        )

        total_amount = (
            liters
            * price_per_liter
        )

        # =================================================
        # PAYMENT
        # =================================================

        if payment_type == "cash":

            if amount_received < total_amount:

                mysql.connection.rollback()

                return jsonify({
                    "success": False,
                    "message": (
                        "Amount received is less "
                        "than the total."
                    ),
                    "total_amount": float(
                        total_amount
                    )
                }), 400

            change_amount = (
                amount_received
                - total_amount
            )

        else:

            amount_received = total_amount

            change_amount = Decimal(
                "0"
            )

        # =================================================
        # CREATE SALE
        # =================================================

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

        # =================================================
        # FUEL SALE
        # =================================================

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

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Fuel sale completed.",
            "sale": {
                "sale_id": sale_id,
                "pump_id": pump_id,
                "fuel_type_id": fuel_type_id,
                "fuel_name": fuel_name,
                "liters": float(liters),
                "price_per_liter": float(
                    price_per_liter
                ),
                "total_amount": float(
                    total_amount
                ),
                "amount_received": float(
                    amount_received
                ),
                "change_amount": float(
                    change_amount
                ),
                "payment_type": payment_type
            }
        }), 201

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not complete fuel sale.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# GET SALE
# GET /api/sales/<sale_id>
# =========================================================

@api_sales_bp.route(
    "/<int:sale_id>",
    methods=["GET"]
)
def get_sale(sale_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                s.sale_id,
                s.sale_date,
                s.sale_type,
                s.subtotal,
                s.total_amount,
                s.payment_type,
                s.amount_received,
                s.change_amount,
                s.status,

                u.full_name,

                c.name AS customer_name

            FROM sales s

            JOIN users u
                ON s.user_id = u.user_id

            LEFT JOIN customers c
                ON s.customer_id = c.customer_id

            WHERE
                s.sale_id = %s
        """, (
            sale_id,
        ))

        sale = cursor.fetchone()

        if not sale:

            return jsonify({
                "success": False,
                "message": "Sale not found."
            }), 404

        result = {
            "sale_id":
                sale["sale_id"],

            "sale_date":
                sale["sale_date"].isoformat()
                if hasattr(
                    sale["sale_date"],
                    "isoformat"
                )
                else sale["sale_date"],

            "sale_type":
                sale["sale_type"],

            "subtotal":
                float(sale["subtotal"] or 0),

            "total_amount":
                float(sale["total_amount"] or 0),

            "payment_type":
                sale["payment_type"],

            "amount_received":
                float(
                    sale["amount_received"] or 0
                ),

            "change_amount":
                float(
                    sale["change_amount"] or 0
                ),

            "status":
                sale["status"],

            "cashier":
                sale["full_name"],

            "customer":
                sale["customer_name"]
        }

        # =================================================
        # STORE SALE ITEMS
        # =================================================

        if sale["sale_type"] == "store":

            cursor.execute("""
                SELECT
                    p.product_id,
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

            item_rows = cursor.fetchall()

            items = []

            for row in item_rows:

                items.append({
                    "product_id":
                        row["product_id"],

                    "product_name":
                        row["product_name"],

                    "quantity":
                        row["quantity"],

                    "unit_price":
                        float(
                            row["unit_price"] or 0
                        ),

                    "subtotal":
                        float(
                            row["subtotal"] or 0
                        )
                })

            result["items"] = items

        # =================================================
        # FUEL SALE
        # =================================================

        elif sale["sale_type"] == "fuel":

            cursor.execute("""
                SELECT
                    fs.pump_id,
                    fp.pump_number,
                    fs.fuel_type_id,
                    ft.fuel_name,
                    fs.liters,
                    fs.price_per_liter,
                    fs.total_amount

                FROM fuel_sales fs

                JOIN fuel_pumps fp
                    ON fs.pump_id = fp.pump_id

                JOIN fuel_types ft
                    ON fs.fuel_type_id = ft.fuel_type_id

                WHERE
                    fs.sale_id = %s
            """, (
                sale_id,
            ))

            fuel = cursor.fetchone()

            if fuel:

                result["fuel"] = {
                    "pump_id":
                        fuel["pump_id"],

                    "pump_number":
                        fuel["pump_number"],

                    "fuel_type_id":
                        fuel["fuel_type_id"],

                    "fuel_name":
                        fuel["fuel_name"],

                    "liters":
                        float(
                            fuel["liters"] or 0
                        ),

                    "price_per_liter":
                        float(
                            fuel["price_per_liter"] or 0
                        ),

                    "total_amount":
                        float(
                            fuel["total_amount"] or 0
                        )
                }

        return jsonify({
            "success": True,
            "sale": result
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not retrieve sale.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()