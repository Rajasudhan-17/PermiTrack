import hashlib
import json
from datetime import date, timedelta
from leave_app.extensions import db
from leave_app.models import Leave, OD, RequestStatus, Role, User, AuditLog, utcnow
from leave_app.services.auth_security import clear_failed_logins


def test_api_login_token_hashing_and_lifecycle(client, seed_data):
    student = seed_data["student"]

    # 1. Login should return raw token
    res = client.post(
        "/api/v1/auth/login",
        json={"username": student.username, "password": "password"}
    )
    assert res.status_code == 200
    data = res.get_json()
    raw_token = data["token"]
    assert len(raw_token) == 64

    # 2. Check DB stores secure hash of token, not plaintext
    db.session.refresh(student)
    stored_hash = student.api_token
    assert stored_hash != raw_token
    assert stored_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    assert student.token_expires_at is not None

    # 3. Test token access works
    res_dash = client.get("/api/v1/dashboard", headers={"X-API-Token": raw_token})
    assert res_dash.status_code == 200
    assert res_dash.get_json()["role"] == "student"

    # 4. Invalidate token and check access is denied
    res_logout = client.post("/api/v1/auth/logout", headers={"X-API-Token": raw_token})
    assert res_logout.status_code == 200

    res_dash_after = client.get("/api/v1/dashboard", headers={"X-API-Token": raw_token})
    assert res_dash_after.status_code == 401


def test_api_login_rate_limiting(client, seed_data):
    # Configure rate limits for testing
    from flask import current_app
    current_app.config["LOGIN_RATE_LIMIT_ENABLED"] = True
    current_app.config["LOGIN_RATE_LIMIT_MAX_ATTEMPTS"] = 5
    current_app.config["LOGIN_RATE_LIMIT_WINDOW_SECONDS"] = 60

    student = seed_data["student"]
    clear_failed_logins(student.username, "127.0.0.1")

    # 1. Run 5 failed attempts
    for _ in range(5):
        res = client.post(
            "/api/v1/auth/login",
            json={"username": student.username, "password": "wrong_password"}
        )
        assert res.status_code == 401

    # 2. 6th attempt must lock out with 429
    res_lock = client.post(
        "/api/v1/auth/login",
        json={"username": student.username, "password": "password"}
    )
    assert res_lock.status_code == 429
    assert "Too many failed sign-in attempts" in res_lock.get_json()["message"]


def test_role_based_pending_queues(client, seed_data):
    student = seed_data["student"]
    mentor = seed_data["mentor"]
    faculty = seed_data["faculty"]
    hod = seed_data["hod"]

    # Clear leaves and ODs first
    db.session.query(Leave).delete()
    db.session.query(OD).delete()
    db.session.commit()

    # 1. Create a Leave request in PENDING state (belongs to Mentor's queue)
    leave_pending = Leave(
        requested_by=student.id,
        approved_by=mentor.id,
        start_date=date.today(),
        end_date=date.today(),
        reason="Dentist appointment",
        status=RequestStatus.PENDING.value
    )
    db.session.add(leave_pending)

    # 2. Create a Leave request in MENTOR_APPROVED state (belongs to Faculty's queue)
    leave_mentor_approved = Leave(
        requested_by=student.id,
        approved_by=faculty.id,
        start_date=date.today(),
        end_date=date.today(),
        reason="Conference",
        status=RequestStatus.MENTOR_APPROVED.value
    )
    db.session.add(leave_mentor_approved)

    # 3. Create a Leave request in FACULTY_APPROVED state (belongs to HOD's queue)
    leave_faculty_approved = Leave(
        requested_by=student.id,
        approved_by=hod.id,
        start_date=date.today(),
        end_date=date.today(),
        reason="Fever",
        status=RequestStatus.FACULTY_APPROVED.value
    )
    db.session.add(leave_faculty_approved)

    db.session.commit()

    # Log in and check queues
    # A. Mentor Queue
    res_mentor_login = client.post("/api/v1/auth/login", json={"username": mentor.username, "password": "password"})
    mentor_token = res_mentor_login.get_json()["token"]
    
    res_mentor_pending = client.get("/api/v1/pending", headers={"X-API-Token": mentor_token})
    assert res_mentor_pending.status_code == 200
    pending_leaves = res_mentor_pending.get_json()["pending_leaves"]
    assert len(pending_leaves) == 1
    assert pending_leaves[0]["id"] == leave_pending.id

    # B. Faculty Queue
    res_faculty_login = client.post("/api/v1/auth/login", json={"username": faculty.username, "password": "password"})
    faculty_token = res_faculty_login.get_json()["token"]

    res_faculty_pending = client.get("/api/v1/pending", headers={"X-API-Token": faculty_token})
    assert res_faculty_pending.status_code == 200
    pending_leaves_f = res_faculty_pending.get_json()["pending_leaves"]
    assert len(pending_leaves_f) == 1
    assert pending_leaves_f[0]["id"] == leave_mentor_approved.id

    # C. HOD Queue
    res_hod_login = client.post("/api/v1/auth/login", json={"username": hod.username, "password": "password"})
    hod_token = res_hod_login.get_json()["token"]

    res_hod_pending = client.get("/api/v1/pending", headers={"X-API-Token": hod_token})
    assert res_hod_pending.status_code == 200
    pending_leaves_h = res_hod_pending.get_json()["pending_leaves"]
    assert len(pending_leaves_h) == 1
    assert pending_leaves_h[0]["id"] == leave_faculty_approved.id


def test_audit_log_actor_capture(client, seed_data):
    student = seed_data["student"]

    # Wipe audit log
    db.session.query(AuditLog).delete()
    db.session.commit()

    # Perform a login request via client
    res = client.post(
        "/api/v1/auth/login",
        json={"username": student.username, "password": "password"}
    )
    assert res.status_code == 200
    token = res.get_json()["token"]

    # Since the request runs through Flask testing client, let's verify if an audit log was created
    # Wait, in api_login, we did not call log_audit_event. Let's trigger a flow that writes logs.
    # E.g., student creates a leave request (which calls submit_leave_request)
    # But wait! We want to test authenticated requests writing audit log actor ID!
    # Let's perform a web logout or password reset or another action that triggers log_audit_event.
    # In auth.py, we have `log_audit_event("LOGIN_SUCCESS", user)`!
    # Let's test that by doing a POST to /login (the HTML form login):
    
    # We first retrieve CSRF token
    res_get = client.get("/")
    assert res_get.status_code == 200
    # The session now has CSRF token. Since CSRF is disabled in conftest.py, we can POST to /login without CSRF token.
    res_login = client.post(
        "/login",
        data={"username": student.username, "password": "password"}
    )
    assert res_login.status_code == 302 # Redirect to index

    # Check AuditLog
    logs = AuditLog.query.all()
    assert len(logs) > 0
    login_log = next(log for log in logs if log.action == "LOGIN_SUCCESS")
    assert login_log.actor_id == student.id
    assert login_log.target_id == student.id
    assert login_log.target_type == "User"


def test_api_pending_risk_shape(client, seed_data):
    student = seed_data["student"]
    mentor = seed_data["mentor"]

    # Clear table records
    db.session.query(Leave).delete()
    db.session.query(OD).delete()
    db.session.commit()

    # Seed one leave and one OD
    leave = Leave(
        requested_by=student.id,
        approved_by=mentor.id,
        start_date=date.today(),
        end_date=date.today(),
        reason="Checkup",
        status=RequestStatus.PENDING.value
    )
    db.session.add(leave)

    coordinator = User(
        username="event_coordinator_risk_shape",
        email="coord_risk_shape@example.com",
        role=Role.EVENT_COORDINATOR.value,
        full_name="Event Coordinator Risk Shape",
    )
    coordinator.set_password("password")
    db.session.add(coordinator)
    db.session.commit()

    od = OD(
        requested_by=student.id,
        faculty_id=seed_data["faculty"].id,
        event_coordinator_id=coordinator.id,
        event_date=date.today(),
        reason="Hackathon",
        status=RequestStatus.PENDING.value
    )
    db.session.add(od)
    db.session.commit()

    # Login as Mentor to view pending leave
    res_login = client.post("/api/v1/auth/login", json={"username": mentor.username, "password": "password"})
    token = res_login.get_json()["token"]

    res_pending = client.get("/api/v1/pending", headers={"X-API-Token": token})
    assert res_pending.status_code == 200
    data = res_pending.get_json()
    
    # Assert leave risk shape
    assert "pending_leaves" in data
    pending_leaves = data["pending_leaves"]
    assert len(pending_leaves) == 1
    leave_item = pending_leaves[0]
    assert "risk" in leave_item
    risk = leave_item["risk"]
    assert isinstance(risk["score"], int)
    assert isinstance(risk["level"], str)
    assert isinstance(risk["reasons"], list)

    # Login as Event Coordinator to view pending OD
    res_login_coord = client.post("/api/v1/auth/login", json={"username": coordinator.username, "password": "password"})
    coord_token = res_login_coord.get_json()["token"]

    res_pending_coord = client.get("/api/v1/pending", headers={"X-API-Token": coord_token})
    assert res_pending_coord.status_code == 200
    data_coord = res_pending_coord.get_json()

    assert "pending_ods" in data_coord
    pending_ods = data_coord["pending_ods"]
    assert len(pending_ods) == 1
    od_item = pending_ods[0]
    assert "risk" in od_item
    risk_od = od_item["risk"]
    assert isinstance(risk_od["score"], int)
    assert isinstance(risk_od["level"], str)
    assert isinstance(risk_od["reasons"], list)


