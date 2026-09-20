import pytest
from datetime import timedelta
from leave_app.models import User, APIToken, EmailQueue, EmailStatus, utcnow
from leave_app.extensions import db
from leave_app.services.emailing import queue_email, process_email_queue


def test_multi_device_api_tokens(client, app):
    """Verify multiple login calls issue unique APIToken entries that remain active concurrently."""
    with app.app_context():
        student = User(username="student_token_test", email="token_test@example.com")
        student.set_password("Password123!")
        db.session.add(student)
        db.session.commit()

    # Login 1 (Device A)
    res1 = client.post("/api/v1/auth/login", json={"username": "student_token_test", "password": "Password123!"})
    assert res1.status_code == 200
    token1 = res1.get_json()["token"]

    # Login 2 (Device B)
    res2 = client.post("/api/v1/auth/login", json={"username": "student_token_test", "password": "Password123!"})
    assert res2.status_code == 200
    token2 = res2.get_json()["token"]

    assert token1 != token2

    # Both tokens work concurrently
    dash1 = client.get("/api/v1/dashboard", headers={"X-API-Token": token1})
    assert dash1.status_code == 200

    dash2 = client.get("/api/v1/dashboard", headers={"X-API-Token": token2})
    assert dash2.status_code == 200

    # Logout Device A
    logout1 = client.post("/api/v1/auth/logout", headers={"X-API-Token": token1})
    assert logout1.status_code == 200

    # Device A token is revoked
    dash1_revoked = client.get("/api/v1/dashboard", headers={"X-API-Token": token1})
    assert dash1_revoked.status_code == 401

    # Device B token remains active!
    dash2_active = client.get("/api/v1/dashboard", headers={"X-API-Token": token2})
    assert dash2_active.status_code == 200


def test_process_email_queue_concurrency(app):
    """Verify process_email_queue processes QUEUED items cleanly and updates status to SENT."""
    with app.app_context():
        queue_email("Concurrency Test Subject", ["test@example.com"], "Test body")
        queued = EmailQueue.query.filter_by(subject="Concurrency Test Subject").first()
        assert queued is not None
        assert queued.status == EmailStatus.QUEUED.value

        processed = process_email_queue()
        assert processed == 1

        db.session.refresh(queued)
        assert queued.status == EmailStatus.SENT.value
