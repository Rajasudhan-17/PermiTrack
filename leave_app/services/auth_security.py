from datetime import timedelta

from flask import current_app
from sqlalchemy.exc import OperationalError, ProgrammingError

from ..extensions import db
from ..models import LoginAttempt, utcnow


def login_rate_limit_key(username, ip_address):
    normalized_username = (username or "").strip().lower()
    normalized_ip = ip_address or "unknown"
    return f"{normalized_username}|{normalized_ip}"


def _login_attempt_table_missing(exc):
    error_text = str(exc).lower()
    return "no such table: login_attempt" in error_text or "doesn't exist" in error_text and "login_attempt" in error_text


def _safe_get_login_attempt(key):
    try:
        return db.session.get(LoginAttempt, key)
    except (OperationalError, ProgrammingError) as exc:
        db.session.rollback()
        if _login_attempt_table_missing(exc):
            current_app.logger.warning(
                "Login rate limit storage is unavailable because the login_attempt table is missing; continuing without it."
            )
            return None
        raise


def login_allowed(username, ip_address):
    if not current_app.config.get("LOGIN_RATE_LIMIT_ENABLED", True):
        return True, None

    attempt = _safe_get_login_attempt(login_rate_limit_key(username, ip_address))
    if not attempt:
        return True, None

    now = utcnow()
    if attempt.locked_until and attempt.locked_until > now:
        return False, attempt.locked_until

    window_seconds = current_app.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"]
    if (now - attempt.window_started_at).total_seconds() > window_seconds:
        db.session.delete(attempt)
        db.session.commit()
        return True, None

    return True, None


def register_failed_login(username, ip_address):
    if not current_app.config.get("LOGIN_RATE_LIMIT_ENABLED", True):
        return

    now = utcnow()
    key = login_rate_limit_key(username, ip_address)
    attempt = _safe_get_login_attempt(key)
    window_seconds = current_app.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"]
    max_attempts = current_app.config["LOGIN_RATE_LIMIT_MAX_ATTEMPTS"]

    if not attempt:
        attempt = LoginAttempt(
            key=key,
            username=(username or "").strip().lower(),
            ip_address=ip_address or "unknown",
            attempt_count=0,
            window_started_at=now,
            last_attempt_at=now,
        )
        db.session.add(attempt)

    if (now - attempt.window_started_at).total_seconds() > window_seconds:
        attempt.attempt_count = 0
        attempt.window_started_at = now
        attempt.locked_until = None

    attempt.attempt_count += 1
    attempt.last_attempt_at = now

    if attempt.attempt_count >= max_attempts:
        attempt.locked_until = now + timedelta(seconds=window_seconds)

    try:
        db.session.commit()
    except (OperationalError, ProgrammingError) as exc:
        db.session.rollback()
        if _login_attempt_table_missing(exc):
            current_app.logger.warning(
                "Skipping failed-login persistence because the login_attempt table is missing."
            )
            return
        raise


def clear_failed_logins(username, ip_address):
    if not current_app.config.get("LOGIN_RATE_LIMIT_ENABLED", True):
        return

    attempt = _safe_get_login_attempt(login_rate_limit_key(username, ip_address))
    if not attempt:
        return

    db.session.delete(attempt)
    try:
        db.session.commit()
    except (OperationalError, ProgrammingError) as exc:
        db.session.rollback()
        if _login_attempt_table_missing(exc):
            current_app.logger.warning(
                "Skipping failed-login cleanup because the login_attempt table is missing."
            )
            return
        raise
