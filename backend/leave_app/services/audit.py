from flask import request
from flask_login import current_user

from ..extensions import db
from ..models import AuditLog, utcnow


def log_audit_event(action, target=None, details=None):
    try:
        actor_id = current_user.id if current_user and current_user.is_authenticated else None
    except Exception:
        actor_id = None

    try:
        ip_address = request.remote_addr if request else "unknown"
    except Exception:
        ip_address = "unknown"

    target_type = None
    target_id = None
    if target is not None:
        try:
            target_type = target.__class__.__name__
            target_id = getattr(target, "id", None)
        except Exception:
            pass

    try:
        log = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            details=details,
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Fallback to current_app logging to prevent app crashes if DB log fails
        from flask import current_app
        current_app.logger.warning(
            "Failed to write structured audit log for action: %s, actor_id: %s, details: %s",
            action,
            actor_id,
            details,
        )
