from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

from .models import Role


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Role.ADMIN.value:
            flash("Admin access required.", "danger")
            return redirect(url_for("main.index"))
        return func(*args, **kwargs)

    return wrapper
