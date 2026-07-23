import os

from flask import Flask
from flask_login import current_user
from dotenv import load_dotenv

load_dotenv()

from config import Config, refresh_runtime_config_values

from .blueprints import register_blueprints
from .commands import register_commands
from .extensions import db, login_manager, mail, migrate
from .security import register_security
from .services.scheduler import register_scheduler
from .services.uploads import configure_uploads
from .services.workflows import pending_counts_for_user, status_badge


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)
    else:
        app.config.from_pyfile("local_config.py", silent=True)

    if app.config.get("TESTING"):
        app.config["ENV_NAME"] = "testing"
        if not test_config or "CSRF_ENABLED" not in test_config:
            app.config["CSRF_ENABLED"] = False
        if not test_config or "LOGIN_RATE_LIMIT_ENABLED" not in test_config:
            app.config["LOGIN_RATE_LIMIT_ENABLED"] = False
        if not test_config or "SESSION_COOKIE_SECURE" not in test_config:
            app.config["SESSION_COOKIE_SECURE"] = False
        if not test_config or "REMEMBER_COOKIE_SECURE" not in test_config:
            app.config["REMEMBER_COOKIE_SECURE"] = False

    refresh_runtime_config_values(app)

    os.makedirs(app.instance_path, exist_ok=True)
    configure_uploads(app)

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    login_manager.init_app(app)

    register_security(app)

    from . import models  # noqa: F401

    register_blueprints(app)
    register_template_helpers(app)
    register_legacy_routes(app)
    register_commands(app)
    register_scheduler(app)
    Config.validate_runtime(app)

    return app


def register_template_helpers(app):
    @app.context_processor
    def inject_template_helpers():
        pending_leave_count, pending_od_count = pending_counts_for_user(current_user)
        return {
            "pending_leave_count": pending_leave_count,
            "pending_od_count": pending_od_count,
            "status_badge": status_badge,
        }


def register_legacy_routes(app):
    app.add_url_rule("/initdb", endpoint="legacy_initdb", view_func=app.view_functions["admin.initdb"])
    app.add_url_rule("/admin_all_ods", endpoint="legacy_admin_all_ods", view_func=app.view_functions["admin.admin_all_ods"])
