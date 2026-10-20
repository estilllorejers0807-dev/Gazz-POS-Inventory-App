from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from database.connection import mysql


reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/manager/analytics")
@login_required
def manager_analytics():

    if current_user.role not in ("manager", "admin"):

        return (
            "Access Denied: You do not have permission "
            "to view managerial analytics.",
            403
        )


    start_date = request.args.get(
        "start_date",
        "2026-01-01"
    )

    end_date = request.args.get(
        "end_date",
        "2026-12-31"
    )


    cursor = mysql.connection.cursor()


    analytics_data = []
    ranked_products = []

    best_selling_product = None
    least_selling_product = None


    fuel_analytics = []
    ranked_fuels = []

    best_selling_fuel = None
    least_selling_fuel = None


    store_summary = {
        "total_sales": 0,
        "total_transactions": 0
    }


    fuel_summary = {
        "total_fuel_sales": 0,
        "total_liters_sold": 0
    }


    low_stock_products = []
    low_stock_fuels = []
    fuel_inventory = []


    try:

        # ============================================================
        # STORE PRODUCT ANALYTICS
        # ============================================================

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


        analytics_data = cursor.fetchall()


        # ============================================================
        # STORE SUMMARY
        # ============================================================

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


        if not store_summary:

            store_summary = {
                "total_sales": 0,
                "total_transactions": 0
            }


        # ============================================================
        # FUEL SUMMARY
        # ============================================================

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


        if not fuel_summary:

            fuel_summary = {
                "total_fuel_sales": 0,
                "total_liters_sold": 0
            }


        # ============================================================
        # FUEL ANALYTICS
        #
        # Fuel profit:
        #
        # (selling price per liter - cost per liter)
        # × liters sold
        #
        # fs.price_per_liter is used for the actual selling price
        # recorded on the fuel sale.
        #
        # ft.cost_per_liter is the fuel cost.
        # ============================================================

        cursor.execute("""

            SELECT

                ft.fuel_type_id,

                ft.fuel_name,

                ft.price_per_liter,

                ft.cost_per_liter,


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
                ) AS total_revenue,


                COALESCE(
                    SUM(
                        CASE

                            WHEN
                                s.status = 'completed'
                                AND s.sale_type = 'fuel'
                                AND DATE(s.sale_date)
                                    BETWEEN %s AND %s

                            THEN
                                (
                                    fs.price_per_liter
                                    - ft.cost_per_liter
                                ) * fs.liters

                            ELSE 0

                        END
                    ),
                    0
                ) AS total_profit


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
                ft.price_per_liter,
                ft.cost_per_liter


            ORDER BY

                total_liters_sold DESC,
                total_revenue DESC,
                ft.fuel_name ASC

        """, (

            start_date,
            end_date,

            start_date,
            end_date,

            start_date,
            end_date

        ))


        fuel_analytics = cursor.fetchall()


        # ============================================================
        # LOW STOCK STORE PRODUCTS
        # ============================================================

        cursor.execute("""

            SELECT

                p.product_name,

                i.stock_quantity,

                p.low_stock_threshold

            FROM inventory i

            JOIN products p

                ON i.product_id = p.product_id

            WHERE

                p.is_active = 1

                AND i.stock_quantity <= p.low_stock_threshold

            ORDER BY

                i.stock_quantity ASC,

                p.product_name ASC

        """)


        low_stock_products = cursor.fetchall()


        # ============================================================
        # LOW STOCK FUEL
        # ============================================================

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
                    <= (fi.tank_capacity * 20 / 100)

            ORDER BY

                fi.current_liters ASC,

                ft.fuel_name ASC

        """)


        low_stock_fuels = cursor.fetchall()


        # ============================================================
        # FULL FUEL INVENTORY
        # ============================================================

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


        fuel_inventory = cursor.fetchall()


        # ============================================================
        # BEST SELLING STORE PRODUCT
        # ============================================================

        best_selling_product = None


        for item in analytics_data:

            quantity = (

                item["total_quantity_sold"]

                if isinstance(item, dict)

                else item[2]

            )


            if quantity > 0:

                best_selling_product = item

                break


        # ============================================================
        # LEAST SELLING STORE PRODUCT
        # ============================================================

        least_selling_product = None


        if analytics_data:

            least_selling_product = sorted(

                analytics_data,

                key=lambda item: (

                    item["total_quantity_sold"]
                    if isinstance(item, dict)
                    else item[2],

                    item["total_revenue"]
                    if isinstance(item, dict)
                    else item[3],

                    item["product_name"]
                    if isinstance(item, dict)
                    else item[1]

                )

            )[0]


        # ============================================================
        # RANK STORE PRODUCTS
        # ============================================================

        ranked_products = []


        for index, item in enumerate(
            analytics_data,
            start=1
        ):

            if isinstance(item, dict):

                product_id = item["product_id"]

                product_name = item["product_name"]

                total_quantity_sold = (
                    item["total_quantity_sold"]
                )

                total_revenue = (
                    item["total_revenue"]
                )

                total_profit = (
                    item["total_profit"]
                )

            else:

                product_id = item[0]

                product_name = item[1]

                total_quantity_sold = item[2]

                total_revenue = item[3]

                total_profit = item[4]


            is_slow_seller = (

                total_quantity_sold > 0

                and total_quantity_sold <= 2

            )


            ranked_products.append({

                "rank": index,

                "product_id": product_id,

                "product_name": product_name,

                "total_quantity_sold":
                    total_quantity_sold,

                "total_revenue":
                    total_revenue,

                "total_profit":
                    total_profit,

                "is_slow_seller":
                    is_slow_seller

            })


        # ============================================================
        # BEST SELLING FUEL
        # ============================================================

        best_selling_fuel = None


        for item in fuel_analytics:

            liters = (

                item["total_liters_sold"]

                if isinstance(item, dict)

                else item[4]

            )


            if liters > 0:

                best_selling_fuel = item

                break


        # ============================================================
        # LEAST SELLING FUEL
        # ============================================================

        least_selling_fuel = None


        if fuel_analytics:

            least_selling_fuel = sorted(

                fuel_analytics,

                key=lambda item: (

                    item["total_liters_sold"]
                    if isinstance(item, dict)
                    else item[4],

                    item["total_revenue"]
                    if isinstance(item, dict)
                    else item[5],

                    item["fuel_name"]
                    if isinstance(item, dict)
                    else item[1]

                )

            )[0]


        # ============================================================
        # RANK FUEL
        # ============================================================

        ranked_fuels = []


        for index, item in enumerate(
            fuel_analytics,
            start=1
        ):

            if isinstance(item, dict):

                fuel_type_id = item["fuel_type_id"]

                fuel_name = item["fuel_name"]

                price_per_liter = (
                    item["price_per_liter"]
                )

                cost_per_liter = (
                    item["cost_per_liter"]
                )

                total_liters_sold = (
                    item["total_liters_sold"]
                )

                total_revenue = (
                    item["total_revenue"]
                )

                total_profit = (
                    item["total_profit"]
                )

            else:

                fuel_type_id = item[0]

                fuel_name = item[1]

                price_per_liter = item[2]

                cost_per_liter = item[3]

                total_liters_sold = item[4]

                total_revenue = item[5]

                total_profit = item[6]


            is_slow_seller = (

                total_liters_sold > 0

                and total_liters_sold <= 20

            )


            ranked_fuels.append({

                "rank": index,

                "fuel_type_id":
                    fuel_type_id,

                "fuel_name":
                    fuel_name,

                "price_per_liter":
                    price_per_liter,

                "cost_per_liter":
                    cost_per_liter,

                "total_liters_sold":
                    total_liters_sold,

                "total_revenue":
                    total_revenue,

                "total_profit":
                    total_profit,

                "is_slow_seller":
                    is_slow_seller

            })


    except Exception as error:

        print(
            f"Analytics SQL Error: {error}"
        )

        analytics_data = []

        ranked_products = []

        best_selling_product = None

        least_selling_product = None


        store_summary = {
            "total_sales": 0,
            "total_transactions": 0
        }


        fuel_summary = {
            "total_fuel_sales": 0,
            "total_liters_sold": 0
        }


        fuel_analytics = []

        ranked_fuels = []

        best_selling_fuel = None

        least_selling_fuel = None


        low_stock_products = []

        low_stock_fuels = []

        fuel_inventory = []


    finally:

        cursor.close()


    return render_template(

        "manager_analytics.html",

        metrics=analytics_data,

        ranked_products=ranked_products,

        best_selling_product=best_selling_product,

        least_selling_product=least_selling_product,

        store_summary=store_summary,

        fuel_summary=fuel_summary,

        low_stock_products=low_stock_products,

        ranked_fuels=ranked_fuels,

        best_selling_fuel=best_selling_fuel,

        least_selling_fuel=least_selling_fuel,

        fuel_inventory=fuel_inventory,

        start_date=start_date,

        end_date=end_date,

        low_stock_fuels=low_stock_fuels

    )