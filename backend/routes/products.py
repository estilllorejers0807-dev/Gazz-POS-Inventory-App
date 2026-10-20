import sys
import os

from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for
)

from flask_login import (
    current_user,
    login_required
)

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    )
)

from database.connection import mysql

products_bp = Blueprint(
    "products",
    __name__
)


def manager_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(401)

        if current_user.role not in (
            "manager",
            "admin"
        ):
            abort(403)

        return view(
            *args,
            **kwargs
        )

    return wrapped_view


@products_bp.route("/products")
@login_required
def products():

    inventory_type = request.args.get(
        "inventory_type",
        "store"
    ).strip().lower()

    if inventory_type not in (
        "store",
        "fuel"
    ):
        inventory_type = "store"

    cursor = mysql.connection.cursor()

    product_list = []
    fuel_list = []

    try:

        if inventory_type == "store":

            cursor.execute("""
                SELECT
                    p.product_id,
                    p.product_name,
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
            """)

            product_list = cursor.fetchall()

        elif inventory_type == "fuel":

            cursor.execute("""
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
            """)

            fuel_list = cursor.fetchall()

    except Exception as error:

        print(
            f"Products page SQL error: {error}"
        )

        product_list = []
        fuel_list = []

        flash(
            f"Could not load inventory: {error}",
            "error"
        )

    finally:

        cursor.close()

    return render_template(
        "products.html",
        products=product_list,
        fuel_products=fuel_list,
        inventory_type=inventory_type
    )


@products_bp.route(
    "/products/add",
    methods=["POST"]
)
@login_required
@manager_required
def add_product():

    product_name = request.form.get(
        "product_name",
        ""
    ).strip()



    unit = request.form.get(
        "unit",
        "piece"
    ).strip()

    try:

        selling_price = Decimal(
            request.form.get(
                "selling_price",
                "0"
            )
        )

        cost_price = Decimal(
            request.form.get(
                "cost_price",
                "0"
            )
        )

        low_stock_threshold = int(
            request.form.get(
                "low_stock_threshold",
                "5"
            )
        )

        starting_stock = int(
            request.form.get(
                "starting_stock",
                "0"
            )
        )

    except (
        ValueError,
        InvalidOperation
    ):

        flash(
            "Please enter valid product details.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

    if not product_name:

        flash(
            "Product name is required.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

    if not unit:

        unit = "piece"

    if (
        selling_price < 0
        or cost_price < 0
        or low_stock_threshold < 0
        or starting_stock < 0
    ):

        flash(
            "Prices and stock values cannot be negative.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO products
            (
                product_name,
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
                1
            )
            """,
            (
                product_name,
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

        flash(
            f"{product_name} was added successfully.",
            "success"
        )

    except Exception as error:

        mysql.connection.rollback()

        flash(
            f"Could not add product: {error}",
            "error"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "products.products"
        )
    )


@products_bp.route(
    "/products/edit/<int:product_id>",
    methods=["POST"]
)
@login_required
@manager_required
def edit_product(product_id):

    product_name = request.form.get(
        "product_name",
        ""
    ).strip()


    unit = request.form.get(
        "unit",
        "piece"
    ).strip()

    try:

        selling_price = Decimal(
            request.form.get(
                "selling_price",
                "0"
            )
        )

        cost_price = Decimal(
            request.form.get(
                "cost_price",
                "0"
            )
        )

        low_stock_threshold = int(
            request.form.get(
                "low_stock_threshold",
                "5"
            )
        )

    except (
        ValueError,
        InvalidOperation
    ):

        flash(
            "Invalid product details.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

    if not product_name:

        flash(
            "Product name is required.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

    if (
        selling_price < 0
        or cost_price < 0
        or low_stock_threshold < 0
    ):

        flash(
            "Prices and stock threshold cannot be negative.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

    cursor = mysql.connection.cursor()

    try:

        cursor.execute(
            """
            UPDATE products

            SET
                product_name = %s,
                unit = %s,
                selling_price = %s,
                cost_price = %s,
                low_stock_threshold = %s

            WHERE
                product_id = %s
            """,
            (
                product_name,
                unit,
                selling_price,
                cost_price,
                low_stock_threshold,
                product_id
            )
        )

        mysql.connection.commit()

        flash(
            "Product updated successfully.",
            "success"
        )

    except Exception as error:

        mysql.connection.rollback()

        flash(
            f"Could not update product: {error}",
            "error"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "products.products"
        )
    )


@products_bp.route(
    "/products/toggle/<int:product_id>",
    methods=["POST"]
)
@login_required
@manager_required
def toggle_product(product_id):

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
            (
                product_id,
            )
        )

        mysql.connection.commit()

        flash(
            "Product status updated successfully.",
            "success"
        )

    except Exception as error:

        mysql.connection.rollback()

        flash(
            f"Could not update product status: {error}",
            "error"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "products.products"
        )
    )


@products_bp.route(
    "/inventory/adjust/<int:product_id>",
    methods=["POST"]
)
@login_required
@manager_required
def adjust_inventory(product_id):

    movement_type = request.form.get(
        "movement_type",
        ""
    )

    reason = request.form.get(
        "reason",
        ""
    ).strip()

    try:

        quantity = int(
            request.form.get(
                "quantity",
                "0"
            )
        )

    except ValueError:

        quantity = 0

    if movement_type not in (
        "stock_in",
        "stock_out",
        "adjustment"
    ):

        flash(
            "Invalid inventory movement type.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

    if quantity <= 0:

        flash(
            "Enter a valid stock quantity.",
            "error"
        )

        return redirect(
            url_for(
                "products.products"
            )
        )

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
            (
                product_id,
            )
        )

        inventory = cursor.fetchone()

        if not inventory:

            flash(
                "Inventory record was not found.",
                "error"
            )

            return redirect(
                url_for(
                    "products.products"
                )
            )

        previous_quantity = inventory[
            "stock_quantity"
        ]

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

            movement_quantity = abs(
                new_quantity
                - previous_quantity
            )

            quantity = movement_quantity

        if new_quantity < 0:

            flash(
                "Stock deduction cannot exceed available stock.",
                "error"
            )

            return redirect(
                url_for(
                    "products.products"
                )
            )

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

        flash(
            "Inventory updated successfully.",
            "success"
        )

    except Exception as error:

        mysql.connection.rollback()

        flash(
            f"Could not update inventory: {error}",
            "error"
        )

    finally:

        cursor.close()

    return redirect(
        url_for(
            "products.products"
        )
    )