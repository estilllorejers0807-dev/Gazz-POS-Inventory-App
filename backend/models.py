from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


# =========================================================
# USERS
# =========================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)

    role = db.Column(
        db.String(50),
        nullable=False,
        default="store_cashier"
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    def get_id(self):
        return str(self.user_id)


# =========================================================
# CATEGORIES
# =========================================================

class Category(db.Model):
    __tablename__ = "categories"

    category_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    category_name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    products = db.relationship(
        "Product",
        backref="category",
        lazy=True
    )


# =========================================================
# PRODUCTS
# =========================================================

class Product(db.Model):
    __tablename__ = "products"

    product_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.category_id"),
        nullable=False
    )

    product_name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.String(255),
        nullable=True
    )

    unit = db.Column(
        db.String(30),
        default="piece"
    )

    selling_price = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0.00
    )

    cost_price = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        default=0.00
    )

    low_stock_threshold = db.Column(
        db.Integer,
        nullable=False,
        default=5
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    inventory = db.relationship(
        "Inventory",
        backref="product",
        uselist=False,
        lazy=True
    )


# =========================================================
# INVENTORY
# =========================================================

class Inventory(db.Model):
    __tablename__ = "inventory"

    inventory_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id"),
        unique=True,
        nullable=False
    )

    stock_quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    last_updated = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


# =========================================================
# INVENTORY MOVEMENTS
# =========================================================

class InventoryMovement(db.Model):
    __tablename__ = "inventory_movements"

    movement_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id"),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    movement_type = db.Column(
        db.Enum(
            "stock_in",
            "stock_out",
            "adjustment"
        ),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    previous_quantity = db.Column(
        db.Integer,
        nullable=False
    )

    new_quantity = db.Column(
        db.Integer,
        nullable=False
    )

    reason = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


# =========================================================
# CUSTOMERS
# =========================================================

class Customer(db.Model):
    __tablename__ = "customers"

    customer_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    phone = db.Column(
        db.String(20),
        nullable=True
    )

    email = db.Column(
        db.String(120),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


# =========================================================
# SALES
# =========================================================

class Sale(db.Model):
    __tablename__ = "sales"

    sale_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    sale_date = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    sale_type = db.Column(
        db.Enum(
            "store",
            "fuel",
            "mixed"
        ),
        nullable=False
    )

    subtotal = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0.00
    )

    total_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0.00
    )

    payment_type = db.Column(
        db.Enum(
            "cash",
            "gcash",
            "other"
        ),
        nullable=False,
        default="cash"
    )

    amount_received = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0.00
    )

    change_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0.00
    )

    status = db.Column(
        db.Enum(
            "completed",
            "cancelled"
        ),
        nullable=False,
        default="completed"
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.customer_id"),
        nullable=True
    )

    items = db.relationship(
        "SaleItem",
        backref="sale",
        lazy=True
    )

    fuel_sales = db.relationship(
        "FuelSale",
        backref="sale",
        lazy=True
    )


# =========================================================
# SALE ITEMS
# =========================================================

class SaleItem(db.Model):
    __tablename__ = "sale_items"

    sale_item_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    sale_id = db.Column(
        db.Integer,
        db.ForeignKey("sales.sale_id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.product_id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    unit_price = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    subtotal = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )


# =========================================================
# FUEL PUMPS
# =========================================================

class FuelPump(db.Model):
    __tablename__ = "fuel_pumps"

    pump_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    pump_number = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )


# =========================================================
# FUEL TYPES
# =========================================================

class FuelType(db.Model):
    __tablename__ = "fuel_types"

    fuel_type_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    fuel_name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    price_per_liter = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0.00
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )


# =========================================================
# FUEL SALES
# =========================================================

class FuelSale(db.Model):
    __tablename__ = "fuel_sales"

    fuel_sale_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    sale_id = db.Column(
        db.Integer,
        db.ForeignKey("sales.sale_id"),
        nullable=False
    )

    pump_id = db.Column(
        db.Integer,
        db.ForeignKey("fuel_pumps.pump_id"),
        nullable=False
    )

    fuel_type_id = db.Column(
        db.Integer,
        db.ForeignKey("fuel_types.fuel_type_id"),
        nullable=False
    )

    product_name = db.Column(
        db.String(100),
        nullable=True
    )

    liters = db.Column(
        db.Numeric(10, 3),
        nullable=False
    )

    price_per_liter = db.Column(
        db.Numeric(10, 2),
        nullable=False
    )

    total_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customers.customer_id"),
        nullable=True
    )


# =========================================================
# FUEL METER READINGS
# =========================================================

class FuelMeterReading(db.Model):
    __tablename__ = "fuel_meter_readings"

    reading_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    pump_id = db.Column(
        db.Integer,
        db.ForeignKey("fuel_pumps.pump_id"),
        nullable=False
    )

    fuel_type_id = db.Column(
        db.Integer,
        db.ForeignKey("fuel_types.fuel_type_id"),
        nullable=False
    )

    reading_date = db.Column(
        db.Date,
        nullable=False
    )

    starting_meter = db.Column(
        db.Numeric(12, 3),
        nullable=False,
        default=0.000
    )

    ending_meter = db.Column(
        db.Numeric(12, 3),
        nullable=False,
        default=0.000
    )

    recorded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.user_id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp()
    )