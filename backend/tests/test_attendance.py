import pytest
from datetime import date, timedelta
from leave_app.models import (
    AttendanceRecord,
    AttendanceStatus,
    ClassGroup,
    Department,
    Leave,
    OD,
    RequestStatus,
    Role,
    User,
    utcnow,
)
from leave_app.extensions import db
from leave_app.services.attendance import (
    get_attendance_sheet,
    get_student_attendance_summary,
    save_attendance_sheet,
    sync_attendance_for_approved_leave,
    sync_attendance_for_approved_od,
)
from leave_app.services.workflows import apply_leave_review, apply_od_review


def test_attendance_auto_detect_leave_and_od_reason(app):
    """Verify attendance sheet automatically detects approved leaves & ODs with student reasons."""
    with app.app_context():
        dept = Department(name="CSE Attendance Dept")
        db.session.add(dept)
        db.session.commit()

        faculty = User(username="fac_att", email="fac_att@example.com", _role=Role.FACULTY.value, department_id=dept.id)
        hod = User(username="hod_att", email="hod_att@example.com", _role=Role.HOD.value, department_id=dept.id)
        faculty.set_password("Pass123!")
        hod.set_password("Pass123!")
        db.session.add_all([faculty, hod])
        db.session.commit()

        dept.hod_id = hod.id
        cg = ClassGroup(department_id=dept.id, year=3, section="A", faculty_id=faculty.id)
        db.session.add(cg)
        db.session.commit()

        student1 = User(
            username="student_leave_att",
            email="s1_att@example.com",
            _role=Role.STUDENT.value,
            department_id=dept.id,
            class_group_id=cg.id,
            register_number="REG001",
        )
        student2 = User(
            username="student_od_att",
            email="s2_att@example.com",
            _role=Role.STUDENT.value,
            department_id=dept.id,
            class_group_id=cg.id,
            register_number="REG002",
        )
        student1.set_password("Pass123!")
        student2.set_password("Pass123!")
        db.session.add_all([student1, student2])
        db.session.commit()

        target_date = date(2026, 10, 15)

        # Create approved Leave for Student 1
        approved_leave = Leave(
            requested_by=student1.id,
            start_date=target_date,
            end_date=target_date,
            reason="Fever and Doctor Consultation",
            status=RequestStatus.APPROVED.value,
            approved_by=hod.id,
        )

        # Create approved OD for Student 2
        approved_od = OD(
            requested_by=student2.id,
            event_date=target_date,
            reason="National Level Robotics Contest",
            status=RequestStatus.APPROVED.value,
            approved_by=hod.id,
        )
        db.session.add_all([approved_leave, approved_od])
        db.session.commit()

        # Load attendance sheet for target date
        sheet = get_attendance_sheet(cg.id, target_date)
        assert len(sheet) == 2

        item1 = next(i for i in sheet if i["student"].id == student1.id)
        item2 = next(i for i in sheet if i["student"].id == student2.id)

        # Check Student 1 auto-detected Leave and reason
        assert item1["status"] == AttendanceStatus.LEAVE.value
        assert "Approved Leave: Fever and Doctor Consultation" in item1["reason"]
        assert item1["is_auto"] is True

        # Check Student 2 auto-detected OD and reason
        assert item2["status"] == AttendanceStatus.OD.value
        assert "Approved OD: National Level Robotics Contest" in item2["reason"]
        assert item2["is_auto"] is True


def test_save_attendance_sheet_and_sync(app):
    """Verify saving attendance sheet and real-time synchronization on HOD approval."""
    with app.app_context():
        dept = Department(name="ECE Attendance Dept")
        db.session.add(dept)
        db.session.commit()

        faculty = User(username="fac_ece", email="fac_ece@example.com", _role=Role.FACULTY.value, department_id=dept.id)
        hod = User(username="hod_ece", email="hod_ece@example.com", _role=Role.HOD.value, department_id=dept.id)
        faculty.set_password("Pass123!")
        hod.set_password("Pass123!")
        db.session.add_all([faculty, hod])
        db.session.commit()

        dept.hod_id = hod.id
        cg = ClassGroup(department_id=dept.id, year=2, section="B", faculty_id=faculty.id)
        db.session.add(cg)
        db.session.commit()

        student = User(
            username="student_sync",
            email="s_sync@example.com",
            _role=Role.STUDENT.value,
            department_id=dept.id,
            class_group_id=cg.id,
            register_number="REG003",
        )
        student.set_password("Pass123!")
        db.session.add(student)
        db.session.commit()

        target_date = date(2026, 11, 20)

        # Save initial attendance (marked as PRESENT)
        records_data = {
            student.id: {
                "status": AttendanceStatus.PRESENT.value,
                "reason": "",
                "leave_id": None,
                "od_id": None,
            }
        }
        count = save_attendance_sheet(cg.id, target_date, records_data, faculty)
        assert count == 1

        rec = AttendanceRecord.query.filter_by(student_id=student.id, date=target_date).first()
        assert rec is not None
        assert rec.status == AttendanceStatus.PRESENT.value

        # Create leave that gets HOD approved
        leave = Leave(
            requested_by=student.id,
            start_date=target_date,
            end_date=target_date,
            reason="Family Function",
            status=RequestStatus.FACULTY_APPROVED.value,
        )
        db.session.add(leave)
        db.session.commit()

        # Approve leave as HOD -> triggers sync_attendance_for_approved_leave
        success, (msg, cat) = apply_leave_review(leave.id, hod.id, "APPROVE", "Approved by HOD")
        assert success is True

        # Verify real-time attendance record sync
        db.session.refresh(rec)
        assert rec.status == AttendanceStatus.LEAVE.value
        assert "Approved Leave: Family Function" in rec.reason

        # Summary check
        summary = get_student_attendance_summary(student.id)
        assert summary["total"] == 1
        assert summary["leave"] == 1
