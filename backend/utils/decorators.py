from functools import wraps

from flask import abort
from flask_login import current_user


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

        return view(*args, **kwargs)

    return wrapped_view


def store_access_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(401)

        allowed_roles = (
            "store_cashier",
            "cashier",
            "manager",
            "admin"
        )

        if current_user.role not in allowed_roles:
            abort(403)

        return view(*args, **kwargs)

    return wrapped_view


def fuel_access_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if not current_user.is_authenticated:
            abort(401)

        allowed_roles = (
            "fuel_cashier",
            "attendant",
            "manager",
            "admin"
        )

        if current_user.role not in allowed_roles:
            abort(403)

        return view(*args, **kwargs)

    return wrapped_view