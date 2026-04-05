import os
import shutil
import tempfile
import unittest
from datetime import date
from io import BytesIO
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from leave_app import create_app
from leave_app.extensions import db
from leave_app.models import ClassGroup, Department, EmailQueue, Leave, OD, RequestStatus, Role, User


class WorkflowTestCase(unittest.TestCase):
    def setUp(self):
        self.upload_dir = tempfile.mkdtemp(dir=os.getcwd())
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "RUN_SCHEDULER": False,
                "ENABLE_INITDB_ROUTE": False,
                "MAIL_USERNAME": "noreply@example.com",
                "OD_UPLOAD_FOLDER": self.upload_dir,
                "LEAVE_UPLOAD_FOLDER": self.upload_dir,
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            self.seed_users()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        try:
            shutil.rmtree(self.upload_dir, ignore_errors=True)
        except OSError:
            pass

    def seed_users(self):
        department = Department(name="Computer Science")
        class_group = ClassGroup(year=2, section="A", department=department)

        admin = User(
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            role=Role.ADMIN.value,
            leave_balance=999,
        )
        admin.set_password("pass123")

        hod = User(
            username="hod",
            email="hod@example.com",
            full_name="HOD User",
            role=Role.HOD.value,
            leave_balance=20,
            department=department,
        )
        hod.set_password("pass123")

        faculty = User(
            username="faculty",
            email="faculty@example.com",
            full_name="Faculty User",
            role=Role.FACULTY.value,
            leave_balance=20,
            department=department,
        )
        faculty.set_password("pass123")

        student = User(
            username="student",
            email="student@example.com",
            full_name="Student User",
            role=Role.STUDENT.value,
            leave_balance=5,
            department=department,
            class_group=class_group,
        )
        student.set_password("pass123")

        db.session.add_all([department, class_group, admin, hod, faculty, student])
        db.session.flush()
        department.hod_id = hod.id
        class_group.faculty_id = faculty.id
        db.session.commit()

    def login(self, username, password="pass123"):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def logout(self):
        return self.client.post("/logout", follow_redirects=True)

    def test_leave_workflow_updates_status_and_balance(self):
        with self.app.app_context():
            student = User.query.filter_by(username="student").first()
            faculty = User.query.filter_by(username="faculty").first()
            leave = Leave(
                requested_by=student.id,
                approved_by=faculty.id,
                start_date=date(2026, 4, 2),
                end_date=date(2026, 4, 3),
                reason="Medical leave",
                status=RequestStatus.PENDING.value,
            )
            db.session.add(leave)
            db.session.commit()
            leave_id = leave.id

        self.login("faculty")
        self.client.post(
            f"/review/{leave_id}",
            data={"action": "APPROVE", "comment": "Forwarding"},
            follow_redirects=True,
        )
        self.logout()

        with self.app.app_context():
            leave = db.session.get(Leave, leave_id)
            student = User.query.filter_by(username="student").first()
            self.assertEqual(leave.status, RequestStatus.FACULTY_APPROVED.value)
            self.assertEqual(student.leave_balance, 5)

        self.login("hod")
        response = self.client.post(
            f"/review/{leave_id}",
            data={"action": "APPROVE", "comment": "Approved"},
            follow_redirects=True,
        )
        self.assertIn(b"Leave fully approved and leave balance updated.", response.data)

        with self.app.app_context():
            leave = db.session.get(Leave, leave_id)
            student = User.query.filter_by(username="student").first()
            self.assertEqual(leave.status, RequestStatus.APPROVED.value)
            self.assertEqual(student.leave_balance, 3)
            self.assertEqual(EmailQueue.query.count(), 2)

    def test_hod_cannot_approve_leave_without_balance(self):
        with self.app.app_context():
            student = User.query.filter_by(username="student").first()
            hod = User.query.filter_by(username="hod").first()
            leave = Leave(
                requested_by=student.id,
                approved_by=hod.id,
                start_date=date(2026, 4, 2),
                end_date=date(2026, 4, 10),
                reason="Long leave",
                status=RequestStatus.FACULTY_APPROVED.value,
            )
            db.session.add(leave)
            db.session.commit()
            leave_id = leave.id

        self.login("hod")
        response = self.client.post(
            f"/review/{leave_id}",
            data={"action": "APPROVE", "comment": "Trying"},
            follow_redirects=True,
        )
        self.assertIn(b"does not have enough leave balance", response.data)

        with self.app.app_context():
            leave = db.session.get(Leave, leave_id)
            student = User.query.filter_by(username="student").first()
            self.assertEqual(leave.status, RequestStatus.FACULTY_APPROVED.value)
            self.assertEqual(student.leave_balance, 5)

    def test_od_workflow_moves_to_final_approval(self):
        with self.app.app_context():
            student = User.query.filter_by(username="student").first()
            faculty = User.query.filter_by(username="faculty").first()
            od = OD(
                requested_by=student.id,
                faculty_id=faculty.id,
                event_date=date(2026, 4, 5),
                reason="Hackathon",
                status=RequestStatus.PENDING.value,
            )
            db.session.add(od)
            db.session.commit()
            od_id = od.id

        self.login("faculty")
        self.client.post(
            f"/review_od/{od_id}",
            data={"action": "APPROVE", "comment": "Faculty approved"},
            follow_redirects=True,
        )
        self.logout()

        with self.app.app_context():
            od = db.session.get(OD, od_id)
            self.assertEqual(od.status, RequestStatus.FACULTY_APPROVED.value)

        self.login("hod")
        response = self.client.post(
            f"/review_od/{od_id}",
            data={"action": "APPROVE", "comment": "HOD approved"},
            follow_redirects=True,
        )
        self.assertIn(b"OD fully approved.", response.data)

        with self.app.app_context():
            od = db.session.get(OD, od_id)
            self.assertEqual(od.status, RequestStatus.APPROVED.value)
            self.assertEqual(EmailQueue.query.count(), 2)

    def test_admin_create_user_requires_class_selection_for_faculty(self):
        self.login("admin")

        with self.app.app_context():
            department = Department.query.filter_by(name="Computer Science").first()

        response = self.client.post(
            "/admin/create_user",
            data={
                "full_name": "New Faculty",
                "username": "faculty2",
                "email": "faculty2@example.com",
                "password": "pass123",
                "role": Role.FACULTY.value,
                "department_id": department.id,
                "class_group_id": "",
            },
            follow_redirects=True,
        )

        self.assertIn(b"Faculty users must be assigned to a department, year, and section.", response.data)

        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(username="faculty2").first())

    def test_model_constraints_block_invalid_rows(self):
        with self.app.app_context():
            department = Department.query.filter_by(name="Computer Science").first()

            invalid_user = User(
                username="bad-user",
                email="bad@example.com",
                full_name="Bad User",
                role=Role.STUDENT.value,
                leave_balance=-1,
                department=department,
            )
            invalid_user.set_password("pass123")
            db.session.add(invalid_user)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

            duplicate_class = ClassGroup(year=2, section="A", department=department)
            db.session.add(duplicate_class)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

            student = User.query.filter_by(username="student").first()
            invalid_leave = Leave(
                requested_by=student.id,
                start_date=date(2026, 4, 6),
                end_date=date(2026, 4, 5),
                reason="Invalid range",
                status=RequestStatus.PENDING.value,
            )
            db.session.add(invalid_leave)
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_emergency_leave_allows_later_proof_upload(self):
        with self.app.app_context():
            student = User.query.filter_by(username="student").first()
            student.leave_balance = 1
            db.session.commit()

        self.login("student")
        response = self.client.post(
            "/apply",
            data={
                "start_date": "2026-04-02",
                "end_date": "2026-04-04",
                "reason": "Emergency medical leave",
                "is_emergency": "on",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Emergency leave submitted in fast-track mode", response.data)

        with self.app.app_context():
            leave = Leave.query.filter_by(reason="Emergency medical leave").first()
            self.assertIsNotNone(leave)
            self.assertTrue(leave.is_emergency)
            self.assertTrue(leave.requires_followup_proof)
            leave_id = leave.id

        with patch("werkzeug.datastructures.file_storage.FileStorage.save", return_value=None):
            upload_response = self.client.post(
                f"/leave/{leave_id}/upload_proof",
                data={"proof": (BytesIO(b"%PDF-1.4 emergency proof"), "proof.pdf")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
        self.assertIn(b"Emergency leave proof uploaded successfully.", upload_response.data)

        with self.app.app_context():
            leave = db.session.get(Leave, leave_id)
            self.assertIsNotNone(leave.proof_filename)
            self.assertFalse(leave.requires_followup_proof)

    def test_faculty_pending_page_shows_conflict_awareness(self):
        with self.app.app_context():
            student = User.query.filter_by(username="student").first()
            faculty = User.query.filter_by(username="faculty").first()

            main_leave = Leave(
                requested_by=student.id,
                approved_by=faculty.id,
                start_date=date(2026, 4, 10),
                end_date=date(2026, 4, 12),
                reason="Primary request",
                status=RequestStatus.PENDING.value,
            )
            leave_two = Leave(
                requested_by=student.id,
                approved_by=faculty.id,
                start_date=date(2026, 4, 10),
                end_date=date(2026, 4, 11),
                reason="Overlap one",
                status=RequestStatus.APPROVED.value,
            )
            leave_three = Leave(
                requested_by=student.id,
                approved_by=faculty.id,
                start_date=date(2026, 4, 11),
                end_date=date(2026, 4, 12),
                reason="Overlap two",
                status=RequestStatus.FACULTY_APPROVED.value,
            )
            od = OD(
                requested_by=student.id,
                faculty_id=faculty.id,
                event_date=date(2026, 4, 11),
                reason="Competition",
                status=RequestStatus.PENDING.value,
            )
            db.session.add_all([main_leave, leave_two, leave_three, od])
            db.session.commit()

        self.login("faculty")
        response = self.client.get("/pending")
        self.assertIn(b"High conflict:", response.data)
        self.assertIn(b"other absence(s) overlap this period", response.data)

    def test_admin_can_export_leave_reports(self):
        with self.app.app_context():
            student = User.query.filter_by(username="student").first()
            leave = Leave(
                requested_by=student.id,
                start_date=date(2026, 4, 15),
                end_date=date(2026, 4, 15),
                reason="Report test",
                status=RequestStatus.PENDING.value,
                is_emergency=True,
            )
            db.session.add(leave)
            db.session.commit()

        self.login("admin")
        csv_response = self.client.get("/admin/reports?request_type=leave&status=PENDING&format=csv")
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response.mimetype, "text/csv")
        self.assertIn(b"Report test", csv_response.data)

        pdf_response = self.client.get("/admin/reports?request_type=leave&status=PENDING&format=pdf")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.mimetype, "application/pdf")
        self.assertTrue(pdf_response.data.startswith(b"%PDF-1.4"))

    def test_csrf_protection_rejects_post_without_token_when_enabled(self):
        csrf_app = create_app(
            {
                "TESTING": True,
                "CSRF_ENABLED": True,
                "LOGIN_RATE_LIMIT_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "RUN_SCHEDULER": False,
                "ENABLE_INITDB_ROUTE": False,
                "MAIL_USERNAME": None,
                "OD_UPLOAD_FOLDER": self.upload_dir,
                "LEAVE_UPLOAD_FOLDER": self.upload_dir,
            }
        )
        csrf_client = csrf_app.test_client()

        with csrf_app.app_context():
            db.create_all()

        response = csrf_client.post("/login", data={"username": "student", "password": "pass123"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"CSRF token missing or invalid", response.data)

        with csrf_app.app_context():
            db.session.remove()
            db.drop_all()


if __name__ == "__main__":
    unittest.main()
