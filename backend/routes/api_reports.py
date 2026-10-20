from flask import (
    Blueprint,
    jsonify,
    request
)

from flask_login import (
    current_user
)

from database.connection import mysql


api_reports_bp = Blueprint(
    "api_reports",
    __name__
)


# =========================================================
# MANAGER / ADMIN CHECK
# =========================================================

def management_access():

    if not current_user.is_authenticated:
        return False

    return current_user.role in (
        "manager",
        "admin"
    )


# =========================================================
# MANAGER ANALYTICS
# GET /api/reports/analytics
# =========================================================

@api_reports_bp.route(
    "/analytics",
    methods=["GET"]
)
def analytics():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not management_access():

        return jsonify({
            "success": False,
            "message": (
                "Manager or admin access required."
            )
        }), 403

    start_date = request.args.get(
        "start_date",
        "2026-01-01"
    )

    end_date = request.args.get(
        "end_date",
        "2026-12-31"
    )

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # STORE PRODUCT ANALYTICS
        # =================================================

        cursor.execute("""
            SELECT

                p.product_id,

                p.product_name,

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                s.status = 'completed'
                                AND s.sale_type = 'store'
                                AND DATE(s.sale_date)
                                    BETWEEN %s AND %s
                            THEN si.quantity
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_quantity_sold,

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                s.status = 'completed'
                                AND s.sale_type = 'store'
                                AND DATE(s.sale_date)
                                    BETWEEN %s AND %s
                            THEN si.subtotal
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_revenue,

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                s.status = 'completed'
                                AND s.sale_type = 'store'
                                AND DATE(s.sale_date)
                                    BETWEEN %s AND %s
                            THEN
                                (
                                    si.unit_price
                                    - p.cost_price
                                ) * si.quantity
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_profit

            FROM products p

            LEFT JOIN sale_items si
                ON p.product_id = si.product_id

            LEFT JOIN sales s
                ON si.sale_id = s.sale_id

            WHERE
                p.is_active = 1

            GROUP BY
                p.product_id,
                p.product_name,
                p.cost_price

            ORDER BY
                total_quantity_sold DESC,
                total_revenue DESC,
                p.product_name ASC

        """, (
            start_date,
            end_date,
            start_date,
            end_date,
            start_date,
            end_date
        ))

        product_rows = cursor.fetchall()

        products = []

        for index, row in enumerate(
            product_rows,
            start=1
        ):

            quantity = int(
                row["total_quantity_sold"] or 0
            )

            products.append({
                "rank": index,
                "product_id":
                    row["product_id"],

                "product_name":
                    row["product_name"],

                "total_quantity_sold":
                    quantity,

                "total_revenue":
                    float(
                        row["total_revenue"] or 0
                    ),

                "total_profit":
                    float(
                        row["total_profit"] or 0
                    ),

                "is_slow_seller":
                    (
                        quantity > 0
                        and quantity <= 2
                    )
            })


        # =================================================
        # STORE SUMMARY
        # =================================================

        cursor.execute("""
            SELECT
                COALESCE(
                    SUM(total_amount),
                    0
                ) AS total_sales,

                COUNT(sale_id)
                    AS total_transactions

            FROM sales

            WHERE
                status = 'completed'
                AND sale_type = 'store'
                AND DATE(sale_date)
                    BETWEEN %s AND %s

        """, (
            start_date,
            end_date
        ))

        store_summary = cursor.fetchone()

        # =================================================
        # FUEL SUMMARY
        # =================================================

        cursor.execute("""
            SELECT
                COALESCE(
                    SUM(fs.total_amount),
                    0
                ) AS total_fuel_sales,

                COALESCE(
                    SUM(fs.liters),
                    0
                ) AS total_liters_sold

            FROM fuel_sales fs

            JOIN sales s
                ON fs.sale_id = s.sale_id

            WHERE
                s.status = 'completed'
                AND s.sale_type = 'fuel'
                AND DATE(s.sale_date)
                    BETWEEN %s AND %s

        """, (
            start_date,
            end_date
        ))

        fuel_summary = cursor.fetchone()

        # =================================================
        # FUEL ANALYTICS
        # =================================================

        cursor.execute("""
            SELECT

                ft.fuel_type_id,

                ft.fuel_name,

                ft.price_per_liter,

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                s.status = 'completed'
                                AND s.sale_type = 'fuel'
                                AND DATE(s.sale_date)
                                    BETWEEN %s AND %s
                            THEN fs.liters
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_liters_sold,

                COALESCE(
                    SUM(
                        CASE
                            WHEN
                                s.status = 'completed'
                                AND s.sale_type = 'fuel'
                                AND DATE(s.sale_date)
                                    BETWEEN %s AND %s
                            THEN fs.total_amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_revenue

            FROM fuel_types ft

            LEFT JOIN fuel_sales fs
                ON ft.fuel_type_id = fs.fuel_type_id

            LEFT JOIN sales s
                ON fs.sale_id = s.sale_id

            WHERE
                ft.is_active = 1

            GROUP BY
                ft.fuel_type_id,
                ft.fuel_name,
                ft.price_per_liter

            ORDER BY
                total_liters_sold DESC,
                total_revenue DESC,
                ft.fuel_name ASC

        """, (
            start_date,
            end_date,
            start_date,
            end_date
        ))

        fuel_rows = cursor.fetchall()

        fuels = []

        for index, row in enumerate(
            fuel_rows,
            start=1
        ):

            liters = float(
                row["total_liters_sold"] or 0
            )

            fuels.append({
                "rank": index,

                "fuel_type_id":
                    row["fuel_type_id"],

                "fuel_name":
                    row["fuel_name"],

                "price_per_liter":
                    float(
                        row["price_per_liter"] or 0
                    ),

                "total_liters_sold":
                    liters,

                "total_revenue":
                    float(
                        row["total_revenue"] or 0
                    ),

                "is_slow_seller":
                    (
                        liters > 0
                        and liters <= 20
                    )
            })


        # =================================================
        # LOW STOCK PRODUCTS
        # =================================================

        cursor.execute("""
            SELECT
                p.product_id,
                p.product_name,
                i.stock_quantity,
                p.low_stock_threshold

            FROM inventory i

            JOIN products p
                ON i.product_id = p.product_id

            WHERE
                p.is_active = 1
                AND i.stock_quantity
                    <= p.low_stock_threshold

            ORDER BY
                i.stock_quantity ASC,
                p.product_name ASC
        """)

        low_product_rows = cursor.fetchall()

        low_stock_products = []

        for row in low_product_rows:

            low_stock_products.append({
                "product_id":
                    row["product_id"],

                "product_name":
                    row["product_name"],

                "stock_quantity":
                    int(
                        row["stock_quantity"]
                    ),

                "low_stock_threshold":
                    int(
                        row["low_stock_threshold"]
                    )
            })


        # =================================================
        # LOW FUEL
        # =================================================

        cursor.execute("""
            SELECT

                fi.inventory_id,

                fi.fuel_type_id,

                ft.fuel_name,

                fi.tank_capacity,

                fi.current_liters,

                CASE
                    WHEN fi.tank_capacity > 0
                    THEN
                        (
                            fi.current_liters
                            / fi.tank_capacity
                        ) * 100
                    ELSE 0
                END AS fuel_level_percentage

            FROM fuel_inventory fi

            JOIN fuel_types ft
                ON fi.fuel_type_id = ft.fuel_type_id

            WHERE
                ft.is_active = 1
                AND fi.tank_capacity > 0
                AND fi.current_liters
                    <= (
                        fi.tank_capacity
                        * 20 / 100
                    )

            ORDER BY
                fi.current_liters ASC,
                ft.fuel_name ASC
        """)

        low_fuel_rows = cursor.fetchall()

        low_stock_fuels = []

        for row in low_fuel_rows:

            low_stock_fuels.append({
                "inventory_id":
                    row["inventory_id"],

                "fuel_type_id":
                    row["fuel_type_id"],

                "fuel_name":
                    row["fuel_name"],

                "tank_capacity":
                    float(
                        row["tank_capacity"] or 0
                    ),

                "current_liters":
                    float(
                        row["current_liters"] or 0
                    ),

                "fuel_level_percentage":
                    float(
                        row[
                            "fuel_level_percentage"
                        ] or 0
                    )
            })


        # =================================================
        # FUEL INVENTORY
        # =================================================

        cursor.execute("""
            SELECT

                fi.inventory_id,

                fi.fuel_type_id,

                ft.fuel_name,

                fi.tank_capacity,

                fi.current_liters

            FROM fuel_inventory fi

            JOIN fuel_types ft
                ON fi.fuel_type_id = ft.fuel_type_id

            WHERE
                ft.is_active = 1

            ORDER BY
                ft.fuel_name ASC
        """)

        fuel_inventory_rows = cursor.fetchall()

        fuel_inventory = []

        for row in fuel_inventory_rows:

            fuel_inventory.append({
                "inventory_id":
                    row["inventory_id"],

                "fuel_type_id":
                    row["fuel_type_id"],

                "fuel_name":
                    row["fuel_name"],

                "tank_capacity":
                    float(
                        row["tank_capacity"] or 0
                    ),

                "current_liters":
                    float(
                        row["current_liters"] or 0
                    )
            })


        # =================================================
        # BEST / LEAST SELLING
        # =================================================

        best_product = None

        for product in products:

            if product[
                "total_quantity_sold"
            ] > 0:

                best_product = product

                break

        least_product = None

        if products:

            least_product = min(
                products,
                key=lambda x: (
                    x["total_quantity_sold"],
                    x["total_revenue"],
                    x["product_name"]
                )
            )

        best_fuel = None

        for fuel in fuels:

            if fuel[
                "total_liters_sold"
            ] > 0:

                best_fuel = fuel

                break

        least_fuel = None

        if fuels:

            least_fuel = min(
                fuels,
                key=lambda x: (
                    x["total_liters_sold"],
                    x["total_revenue"],
                    x["fuel_name"]
                )
            )


        return jsonify({
            "success": True,

            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },

            "store_summary": {
                "total_sales":
                    float(
                        store_summary[
                            "total_sales"
                        ] or 0
                    ),

                "total_transactions":
                    int(
                        store_summary[
                            "total_transactions"
                        ] or 0
                    )
            },

            "fuel_summary": {
                "total_fuel_sales":
                    float(
                        fuel_summary[
                            "total_fuel_sales"
                        ] or 0
                    ),

                "total_liters_sold":
                    float(
                        fuel_summary[
                            "total_liters_sold"
                        ] or 0
                    )
            },

            "products": products,

            "fuels": fuels,

            "best_selling_product":
                best_product,

            "least_selling_product":
                least_product,

            "best_selling_fuel":
                best_fuel,

            "least_selling_fuel":
                least_fuel,

            "low_stock_products":
                low_stock_products,

            "low_stock_fuels":
                low_stock_fuels,

            "fuel_inventory":
                fuel_inventory

        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not generate analytics.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()