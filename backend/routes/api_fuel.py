from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    jsonify,
    request
)

from flask_login import (
    current_user
)

from database.connection import mysql


api_fuel_bp = Blueprint(
    "api_fuel",
    __name__
)


# =========================================================
# HELPER
# =========================================================

def fuel_access():

    if not current_user.is_authenticated:
        return False

    return current_user.role in (
        "admin",
        "manager",
        "fuel_cashier",
        "attendant"
    )


def decimal_to_float(value):

    if value is None:
        return 0

    return float(value)


# =========================================================
# GET FUEL INFORMATION
# GET /api/fuel
# =========================================================

@api_fuel_bp.route(
    "/",
    methods=["GET"]
)
def get_fuel():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not fuel_access():

        return jsonify({
            "success": False,
            "message": "Fuel access required."
        }), 403

    cursor = mysql.connection.cursor()

    try:

        # =================================================
        # FUEL TYPES
        # =================================================

        cursor.execute("""
            SELECT
                fuel_type_id,
                fuel_name,
                price_per_liter
            FROM fuel_types
            WHERE is_active = 1
            ORDER BY fuel_name
        """)

        fuel_rows = cursor.fetchall()

        fuel_types = []

        for row in fuel_rows:

            fuel_types.append({
                "fuel_type_id": row["fuel_type_id"],
                "fuel_name": row["fuel_name"],
                "price_per_liter":
                    decimal_to_float(
                        row["price_per_liter"]
                    )
            })


        # =================================================
        # PUMPS
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
                p.is_active = 1
                AND f.is_active = 1

            ORDER BY p.pump_number
        """)

        pump_rows = cursor.fetchall()

        pumps = []

        for row in pump_rows:

            pumps.append({
                "pump_id": row["pump_id"],
                "pump_number": row["pump_number"],
                "fuel_type_id": row["fuel_type_id"],
                "fuel_name": row["fuel_name"],
                "price_per_liter":
                    decimal_to_float(
                        row["price_per_liter"]
                    )
            })


        # =================================================
        # METER READINGS
        # =================================================

        cursor.execute("""
            SELECT
                r.reading_id,
                p.pump_number,
                f.fuel_name,
                r.reading_date,
                r.starting_meter,
                r.ending_meter,

                (
                    r.ending_meter
                    - r.starting_meter
                ) AS liters_sold,

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

        reading_rows = cursor.fetchall()

        readings = []

        for row in reading_rows:

            reading_date = row["reading_date"]

            if hasattr(
                reading_date,
                "isoformat"
            ):
                reading_date = (
                    reading_date.isoformat()
                )

            readings.append({
                "reading_id":
                    row["reading_id"],

                "pump_number":
                    row["pump_number"],

                "fuel_name":
                    row["fuel_name"],

                "reading_date":
                    reading_date,

                "starting_meter":
                    decimal_to_float(
                        row["starting_meter"]
                    ),

                "ending_meter":
                    decimal_to_float(
                        row["ending_meter"]
                    ),

                "liters_sold":
                    decimal_to_float(
                        row["liters_sold"]
                    ),

                "recorded_by":
                    row["full_name"]
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
                ft.fuel_name
        """)

        inventory_rows = cursor.fetchall()

        inventory = []

        for row in inventory_rows:

            capacity = Decimal(
                str(
                    row["tank_capacity"] or 0
                )
            )

            current = Decimal(
                str(
                    row["current_liters"] or 0
                )
            )

            percentage = 0

            if capacity > 0:
                percentage = (
                    current / capacity
                ) * 100

            inventory.append({
                "inventory_id":
                    row["inventory_id"],

                "fuel_type_id":
                    row["fuel_type_id"],

                "fuel_name":
                    row["fuel_name"],

                "tank_capacity":
                    float(capacity),

                "current_liters":
                    float(current),

                "level_percentage":
                    float(percentage)
            })


        return jsonify({
            "success": True,
            "fuel_types": fuel_types,
            "pumps": pumps,
            "readings": readings,
            "inventory": inventory
        }), 200

    except Exception as error:

        return jsonify({
            "success": False,
            "message": "Could not load fuel information.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# ADD METER READING
# POST /api/fuel/readings
# =========================================================

@api_fuel_bp.route(
    "/readings",
    methods=["POST"]
)
def add_meter_reading():

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if not fuel_access():

        return jsonify({
            "success": False,
            "message": "Fuel access required."
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

        reading_date = datetime.strptime(
            data.get("reading_date"),
            "%Y-%m-%d"
        ).date()

        starting_meter = Decimal(
            str(
                data.get("starting_meter")
            )
        )

        ending_meter = Decimal(
            str(
                data.get("ending_meter")
            )
        )

    except (
        ValueError,
        TypeError,
        InvalidOperation
    ):

        return jsonify({
            "success": False,
            "message": "Invalid meter-reading details."
        }), 400

    if starting_meter < 0:

        return jsonify({
            "success": False,
            "message": "Starting meter cannot be negative."
        }), 400

    if ending_meter < 0:

        return jsonify({
            "success": False,
            "message": "Ending meter cannot be negative."
        }), 400

    if ending_meter < starting_meter:

        return jsonify({
            "success": False,
            "message": (
                "Ending meter cannot be lower "
                "than starting meter."
            )
        }), 400

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

            return jsonify({
                "success": False,
                "message": "Fuel pump is not available."
            }), 404

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
            pump["fuel_type_id"],
            reading_date,
            starting_meter,
            ending_meter,
            current_user.id
        ))

        reading_id = cursor.lastrowid

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Fuel meter reading recorded.",
            "reading_id": reading_id,
            "liters_sold": float(
                ending_meter - starting_meter
            )
        }), 201

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not save meter reading.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()


# =========================================================
# UPDATE FUEL INVENTORY
# POST /api/fuel/inventory/<fuel_type_id>
# =========================================================

@api_fuel_bp.route(
    "/inventory/<int:fuel_type_id>",
    methods=["POST"]
)
def update_fuel_inventory(fuel_type_id):

    if not current_user.is_authenticated:

        return jsonify({
            "success": False,
            "message": "Authentication required."
        }), 401

    if current_user.role not in (
        "admin",
        "manager"
    ):

        return jsonify({
            "success": False,
            "message": "Manager or admin access required."
        }), 403

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "message": "JSON data is required."
        }), 400

    movement_type = data.get(
        "movement_type",
        ""
    ).strip()

    reason = data.get(
        "reason",
        ""
    ).strip()

    try:

        quantity = Decimal(
            str(
                data.get(
                    "quantity",
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
            "message": "Invalid liter quantity."
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

            return jsonify({
                "success": False,
                "message": "Fuel inventory not found."
            }), 404

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

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": (
                    "Fuel deduction cannot exceed "
                    "available liters."
                )
            }), 400

        if new_liters > tank_capacity:

            mysql.connection.rollback()

            return jsonify({
                "success": False,
                "message": (
                    "Fuel quantity cannot exceed "
                    f"tank capacity of "
                    f"{tank_capacity:.3f} L."
                )
            }), 400

        cursor.execute("""
            UPDATE fuel_inventory

            SET current_liters = %s

            WHERE fuel_type_id = %s
        """, (
            new_liters,
            fuel_type_id
        ))

        mysql.connection.commit()

        return jsonify({
            "success": True,
            "message": "Fuel inventory updated.",
            "fuel_type_id": fuel_type_id,
            "previous_liters": float(
                previous_liters
            ),
            "new_liters": float(
                new_liters
            ),
            "reason": (
                reason
                or "Manual fuel inventory update"
            )
        }), 200

    except Exception as error:

        mysql.connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not update fuel inventory.",
            "error": str(error)
        }), 500

    finally:

        cursor.close()