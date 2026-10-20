from flask import Blueprint, jsonify, request
from flask_login import current_user

from decimal import Decimal, InvalidOperation

from database.connection import mysql


api_products_bp = Blueprint(
    "api_products",
    __name__
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def manager_or_admin():

    if not current_user.is_authenticated:
        return False

    return current_user.role in (
        "manager",
        "admin"
    )


def decimal_value(value):

    try:
        return Decimal(str(value))
    except (
        ValueError,
        InvalidOperation,
        TypeError
    ):
        return None


def product_to_dict(row):

    if not row:
        return None

    return {
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "description": row.get("description"),
        "unit": row["unit"],
        "selling_price": float(
            row["selling_price"] or 0
        ),
        "cost_price": float(
            row["cost_price"] or 0
        ),
        "low_stock_threshold": row[
            "low_stock_threshold"
        ],
        "is_active": bool(
            row["is_active"]
        ),
        "stock_quantity": int(
            row["stock_quantity"] or 0
        )
    }


# =========================================================
# GET PRODUCTS
# GET /api/products
# =========================================================

@api_products_bp.route(
    "/",
    methods=["GET"]
)
def get_products():

    inventory_type = request.args.get(
        "inventory_type",
        "store"
    ).strip().lower()

    if inventory_type not in (
        "store",
        "fuel"
    ):

        return jsonify({
            "success": False,
            "message": "Invalid inventory type."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        # =============================================
        # STORE PRODUCTS
        # =============================================

        if inventory_type == "store":

            cursor.execute(
                """
                SELECT
                    p.product_id,
                    p.product_name,
                    p.description,
                    p.unit,
                    p.selling_price,
                    p.cost_price,
                    p.low_stock_threshold,
                    p.is_active,

                    COALESCE(
                        i.stock_quantity,
                        0
                    ) AS stock_quantity

                FROM products p

                LEFT JOIN inventory i
                    ON p.product_id = i.product_id

                ORDER BY
                    p.product_name
                """
            )

            rows = cursor.fetchall()

            products = [
                product_to_dict(row)
                for row in rows
            ]

            return jsonify({
                "success": True,
                "inventory_type": "store",
                "products": products
            }), 200

        # =============================================
        # FUEL
        # =============================================

        cursor.execute(
            """
            SELECT
                ft.fuel_type_id,
                ft.fuel_name,
                ft.price_per_liter,

                COALESCE(
                    fi.tank_capacity,
                    0
                ) AS tank_capacity,

                COALESCE(
                    fi.current_liters,
                    0
                ) AS current_liters

            FROM fuel_types ft

            LEFT JOIN fuel_inventory fi
                ON ft.fuel_type_id = fi.fuel_type_id

            WHERE
                ft.is_active = 1

            ORDER BY
                ft.fuel_name
            """
        )

        rows = cursor.fetchall()

        fuel = []

        for row in rows:

            fuel.append({
                "fuel_type_id": row[
                    "fuel_type_id"
                ],
                "fuel_name": row[
                    "fuel_name"
                ],
                "price_per_liter": float(
                    row["price_per_liter"] or 0
                ),
                "tank_capacity": float(
                    row["tank_capacity"] or 0
                ),
                "current_liters": float(
                    row["current_liters"] or 0
                )
            })

        return jsonify({
            "success": True,
            "inventory_type": "fuel",
            "fuel": fuel
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not load inventory.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# GET ONE PRODUCT
# GET /api/products/<product_id>
# =========================================================

@api_products_bp.route(
    "/<int:product_id>",
    methods=["GET"]
)
def get_product(product_id):

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.description,
                p.unit,
                p.selling_price,
                p.cost_price,
                p.low_stock_threshold,
                p.is_active,

                COALESCE(
                    i.stock_quantity,
                    0
                ) AS stock_quantity

            FROM products p

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.product_id = %s
            """,
            (product_id,)
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "success": False,
                "message": "Product not found."
            }), 404

        return jsonify({
            "success": True,
            "product": product_to_dict(product)
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not retrieve product.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# CREATE PRODUCT
# POST /api/products
# =========================================================

@api_products_bp.route(
    "/",
    methods=["POST"]
)
def create_product():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not manager_or_admin():

        return jsonify({
            "success": False,
            "message": "Manager or admin access required."
        }), 403

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    product_name = data.get(
        "product_name",
        ""
    ).strip()

    description = data.get(
        "description",
        ""
    ).strip()

    unit = data.get(
        "unit",
        "piece"
    ).strip()

    selling_price = decimal_value(
        data.get(
            "selling_price",
            0
        )
    )

    cost_price = decimal_value(
        data.get(
            "cost_price",
            0
        )
    )

    try:

        low_stock_threshold = int(
            data.get(
                "low_stock_threshold",
                5
            )
        )

        starting_stock = int(
            data.get(
                "starting_stock",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": "Invalid stock values."
        }), 400

    if not product_name:

        return jsonify({
            "success": False,
            "message": "Product name is required."
        }), 400

    if selling_price is None or cost_price is None:

        return jsonify({
            "success": False,
            "message": "Invalid price values."
        }), 400

    if (
        selling_price < 0
        or cost_price < 0
        or low_stock_threshold < 0
        or starting_stock < 0
    ):

        return jsonify({
            "success": False,
            "message": "Prices and stock cannot be negative."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO products
            (
                product_name,
                description,
                unit,
                selling_price,
                cost_price,
                low_stock_threshold,
                is_active
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                1
            )
            """,
            (
                product_name,
                description or None,
                unit,
                selling_price,
                cost_price,
                low_stock_threshold
            )
        )

        product_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO inventory
            (
                product_id,
                stock_quantity
            )
            VALUES
            (
                %s,
                %s
            )
            """,
            (
                product_id,
                starting_stock
            )
        )

        if starting_stock > 0:

            cursor.execute(
                """
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
                    'stock_in',
                    %s,
                    0,
                    %s,
                    %s
                )
                """,
                (
                    product_id,
                    current_user.id,
                    starting_stock,
                    starting_stock,
                    "Initial stock for new product"
                )
            )

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Product created successfully.",
            "product_id": product_id
        }), 201

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not create product.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# UPDATE PRODUCT
# PUT /api/products/<product_id>
# =========================================================

@api_products_bp.route(
    "/<int:product_id>",
    methods=["PUT"]
)
def update_product(product_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not manager_or_admin():

        return jsonify({
            "success": False,
            "message": "Manager or admin access required."
        }), 403

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    product_name = data.get(
        "product_name",
        ""
    ).strip()

    description = data.get(
        "description",
        ""
    ).strip()

    unit = data.get(
        "unit",
        "piece"
    ).strip()

    selling_price = decimal_value(
        data.get("selling_price", 0)
    )

    cost_price = decimal_value(
        data.get("cost_price", 0)
    )

    try:

        low_stock_threshold = int(
            data.get(
                "low_stock_threshold",
                5
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": "Invalid low stock threshold."
        }), 400

    if not product_name:

        return jsonify({
            "success": False,
            "message": "Product name is required."
        }), 400

    if selling_price is None or cost_price is None:

        return jsonify({
            "success": False,
            "message": "Invalid price."
        }), 400

    if (
        selling_price < 0
        or cost_price < 0
        or low_stock_threshold < 0
    ):

        return jsonify({
            "success": False,
            "message": "Values cannot be negative."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            UPDATE products

            SET
                product_name = %s,
                description = %s,
                unit = %s,
                selling_price = %s,
                cost_price = %s,
                low_stock_threshold = %s

            WHERE
                product_id = %s
            """,
            (
                product_name,
                description or None,
                unit,
                selling_price,
                cost_price,
                low_stock_threshold,
                product_id
            )
        )

        if cursor.rowcount == 0:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": "Product not found."
            }), 404

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Product updated successfully."
        }), 200

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not update product.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# TOGGLE PRODUCT STATUS
# PATCH /api/products/<product_id>/status
# =========================================================

@api_products_bp.route(
    "/<int:product_id>/status",
    methods=["PATCH"]
)
def toggle_product(product_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not manager_or_admin():

        return jsonify({
            "success": False,
            "message": "Manager or admin access required."
        }), 403

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            UPDATE products

            SET
                is_active = NOT is_active

            WHERE
                product_id = %s
            """,
            (product_id,)
        )

        if cursor.rowcount == 0:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": "Product not found."
            }), 404

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Product status updated successfully."
        }), 200

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not update product status.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# ADJUST INVENTORY
# POST /api/products/<product_id>/inventory
# =========================================================

@api_products_bp.route(
    "/<int:product_id>/inventory",
    methods=["POST"]
)
def adjust_inventory(product_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not manager_or_admin():

        return jsonify({
            "success": False,
            "message": "Manager or admin access required."
        }), 403

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    movement_type = data.get(
        "movement_type",
        ""
    )

    reason = data.get(
        "reason",
        ""
    ).strip()

    try:

        quantity = int(
            data.get(
                "quantity",
                0
            )
        )

    except (
        ValueError,
        TypeError
    ):

        return jsonify({
            "success": False,
            "message": "Invalid quantity."
        }), 400

    if movement_type not in (
        "stock_in",
        "stock_out",
        "adjustment"
    ):

        return jsonify({
            "success": False,
            "message": "Invalid movement type."
        }), 400

    if quantity <= 0:

        return jsonify({
            "success": False,
            "message": "Quantity must be greater than zero."
        }), 400

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                stock_quantity

            FROM inventory

            WHERE
                product_id = %s

            FOR UPDATE
            """,
            (product_id,)
        )

        inventory = cursor.fetchone()

        if not inventory:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": "Inventory record not found."
            }), 404

        previous_quantity = int(
            inventory["stock_quantity"]
        )

        if movement_type == "stock_in":

            new_quantity = (
                previous_quantity
                + quantity
            )

        elif movement_type == "stock_out":

            new_quantity = (
                previous_quantity
                - quantity
            )

        else:

            new_quantity = quantity

            quantity = abs(
                new_quantity
                - previous_quantity
            )

        if new_quantity < 0:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": "Stock deduction exceeds available stock."
            }), 400

        cursor.execute(
            """
            UPDATE inventory

            SET
                stock_quantity = %s

            WHERE
                product_id = %s
            """,
            (
                new_quantity,
                product_id
            )
        )

        cursor.execute(
            """
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
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                product_id,
                current_user.id,
                movement_type,
                quantity,
                previous_quantity,
                new_quantity,
                reason or "Manual inventory update"
            )
        )

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Inventory updated successfully.",
            "product_id": product_id,
            "previous_quantity": previous_quantity,
            "new_quantity": new_quantity
        }), 200

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not update inventory.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()