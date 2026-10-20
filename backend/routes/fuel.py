from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database.connection import mysql
from utils.decorators import fuel_access_required


fuel_bp = Blueprint("fuel", __name__)


@fuel_bp.route("/fuel")
@login_required
@fuel_access_required
def fuel():

    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                fuel_type_id,
                fuel_name,
                price_per_liter
            FROM fuel_types
            WHERE is_active = 1
            ORDER BY fuel_name
        """)

        fuel_types = cursor.fetchall()


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


        cursor.execute("""
            SELECT
                r.reading_id,
                p.pump_number,
                f.fuel_name,
                r.reading_date,
                r.starting_meter,
                r.ending_meter,
                (r.ending_meter - r.starting_meter) AS liters_sold,
                u.full_name
            FROM fuel_meter_readings r
            JOIN fuel_pumps p
                ON r.pump_id = p.pump_id
            JOIN fuel_types f
                ON p.fuel_type_id = f.fuel_type_id
            JOIN users u
                ON r.recorded_by = u.user_id
            ORDER BY
                r.reading_date DESC,
                r.reading_id DESC
            LIMIT 20
        """)

        readings = cursor.fetchall()


    except Exception as error:

        flash(
            f"Could not load fuel information: {error}",
            "error"
        )

        fuel_types = []
        pumps = []
        readings = []


    finally:

        cursor.close()


    return render_template(
        "fuel_pos.html",
        fuel_types=fuel_types,
        pumps=pumps,
        readings=readings
    )


@fuel_bp.route(
    "/fuel/readings/add",
    methods=["POST"]
)
@login_required
@fuel_access_required
def add_meter_reading():

    try:

        pump_id = int(
            request.form.get(
                "pump_id",
                ""
            )
        )

        reading_date = datetime.strptime(
            request.form.get(
                "reading_date",
                ""
            ),
            "%Y-%m-%d"
        ).date()

        starting_meter = Decimal(
            request.form.get(
                "starting_meter",
                ""
            )
        )

        ending_meter = Decimal(
            request.form.get(
                "ending_meter",
                ""
            )
        )

    except (
        ValueError,
        InvalidOperation
    ):

        flash(
            "Please enter valid meter-reading details.",
            "error"
        )

        return redirect(
            url_for("fuel.fuel")
        )


    if starting_meter < 0:

        flash(
            "Starting meter reading cannot be negative.",
            "error"
        )

        return redirect(
            url_for("fuel.fuel")
        )


    if ending_meter < 0:

        flash(
            "Ending meter reading cannot be negative.",
            "error"
        )

        return redirect(
            url_for("fuel.fuel")
        )


    if ending_meter < starting_meter:

        flash(
            "Ending meter reading cannot be lower than the starting meter reading.",
            "error"
        )

        return redirect(
            url_for("fuel.fuel")
        )


    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                p.pump_id,
                p.fuel_type_id,
                f.fuel_name
            FROM fuel_pumps p
            JOIN fuel_types f
                ON p.fuel_type_id = f.fuel_type_id
            WHERE
                p.pump_id = %s
                AND p.is_active = 1
                AND f.is_active = 1
        """, (
            pump_id,
        ))

        pump = cursor.fetchone()


        if not pump:

            flash(
                "Selected fuel pump is not available.",
                "error"
            )

            return redirect(
                url_for("fuel.fuel")
            )


        fuel_type_id = pump["fuel_type_id"]


        cursor.execute("""
            INSERT INTO fuel_meter_readings
            (
                pump_id,
                fuel_type_id,
                reading_date,
                starting_meter,
                ending_meter,
                recorded_by
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
            pump_id,
            fuel_type_id,
            reading_date,
            starting_meter,
            ending_meter,
            current_user.id
        ))


        mysql.connection.commit()


        flash(
            "Fuel meter reading was recorded successfully.",
            "success"
        )


    except Exception as error:

        mysql.connection.rollback()

        flash(
            f"Could not save meter reading: {error}",
            "error"
        )


    finally:

        cursor.close()


    return redirect(
        url_for("fuel.fuel")
    )


@fuel_bp.route(
    "/fuel/inventory/update/<int:fuel_type_id>",
    methods=["POST"]
)
@login_required
@fuel_access_required
def update_fuel_inventory(fuel_type_id):

    movement_type = request.form.get(
        "movement_type",
        ""
    ).strip()


    reason = request.form.get(
        "reason",
        ""
    ).strip()


    try:

        quantity = Decimal(
            request.form.get(
                "quantity",
                "0"
            )
        )


    except InvalidOperation:

        flash(
            "Please enter a valid liter quantity.",
            "error"
        )

        return redirect(
            url_for(
                "products.products",
                inventory_type="fuel"
            )
        )


    if movement_type not in (
        "stock_in",
        "stock_out",
        "adjustment"
    ):

        flash(
            "Invalid fuel inventory movement type.",
            "error"
        )

        return redirect(
            url_for(
                "products.products",
                inventory_type="fuel"
            )
        )


    if quantity <= 0:

        flash(
            "Liter quantity must be greater than zero.",
            "error"
        )

        return redirect(
            url_for(
                "products.products",
                inventory_type="fuel"
            )
        )


    cursor = mysql.connection.cursor()

    try:

        cursor.execute("""
            SELECT
                inventory_id,
                tank_capacity,
                current_liters
            FROM fuel_inventory
            WHERE fuel_type_id = %s
            FOR UPDATE
        """, (
            fuel_type_id,
        ))

        inventory = cursor.fetchone()


        if not inventory:

            flash(
                "Fuel inventory record was not found.",
                "error"
            )

            return redirect(
                url_for(
                    "products.products",
                    inventory_type="fuel"
                )
            )


        tank_capacity = Decimal(
            str(
                inventory["tank_capacity"]
            )
        )


        previous_liters = Decimal(
            str(
                inventory["current_liters"]
            )
        )


        if movement_type == "stock_in":

            new_liters = (
                previous_liters
                + quantity
            )


        elif movement_type == "stock_out":

            new_liters = (
                previous_liters
                - quantity
            )


        else:

            new_liters = quantity


        if new_liters < 0:

            flash(
                "Fuel deduction cannot exceed the available liters.",
                "error"
            )

            return redirect(
                url_for(
                    "products.products",
                    inventory_type="fuel"
                )
            )


        if new_liters > tank_capacity:

            flash(
                f"Fuel quantity cannot exceed tank capacity of {tank_capacity:.3f} L.",
                "error"
            )

            return redirect(
                url_for(
                    "products.products",
                    inventory_type="fuel"
                )
            )


        cursor.execute("""
            UPDATE fuel_inventory
            SET current_liters = %s
            WHERE fuel_type_id = %s
        """, (
            new_liters,
            fuel_type_id
        ))


        mysql.connection.commit()


        flash(
            "Fuel inventory updated successfully.",
            "success"
        )


    except Exception as error:

        mysql.connection.rollback()

        flash(
            f"Could not update fuel inventory: {error}",
            "error"
        )


    finally:

        cursor.close()


    return redirect(
        url_for(
            "products.products",
            inventory_type="fuel"
        )
    )