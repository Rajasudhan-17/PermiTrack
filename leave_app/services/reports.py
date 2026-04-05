import csv
import io
from datetime import datetime

from sqlalchemy import extract

from ..models import ClassGroup, Department, Leave, OD, RequestStatus, User


def parse_month_filter(month_value):
    if not month_value:
        return None, None

    try:
        parsed = datetime.strptime(month_value, "%Y-%m")
    except ValueError:
        return None, None
    return parsed.year, parsed.month


def build_report_filters(args):
    request_type = args.get("request_type", "leave")
    department_id = args.get("department_id", type=int)
    class_group_id = args.get("class_group_id", type=int)
    status = args.get("status") or None
    month = args.get("month") or None
    year, month_number = parse_month_filter(month) if month else (None, None)

    return {
        "request_type": request_type if request_type in {"leave", "od"} else "leave",
        "department_id": department_id,
        "class_group_id": class_group_id,
        "status": status if status in {item.value for item in RequestStatus} else None,
        "month": month,
        "year": year,
        "month_number": month_number,
    }


def query_report_rows(filters):
    if filters["request_type"] == "leave":
        query = Leave.query.join(User, User.id == Leave.requested_by)
        if filters["department_id"]:
            query = query.filter(User.department_id == filters["department_id"])
        if filters["class_group_id"]:
            query = query.filter(User.class_group_id == filters["class_group_id"])
        if filters["status"]:
            query = query.filter(Leave.status == filters["status"])
        if filters["year"] and filters["month_number"]:
            query = query.filter(
                extract("year", Leave.start_date) == filters["year"],
                extract("month", Leave.start_date) == filters["month_number"],
            )
        return query.order_by(Leave.applied_on.desc()).all()

    query = OD.query.join(User, User.id == OD.requested_by)
    if filters["department_id"]:
        query = query.filter(User.department_id == filters["department_id"])
    if filters["class_group_id"]:
        query = query.filter(User.class_group_id == filters["class_group_id"])
    if filters["status"]:
        query = query.filter(OD.status == filters["status"])
    if filters["year"] and filters["month_number"]:
        query = query.filter(
            extract("year", OD.event_date) == filters["year"],
            extract("month", OD.event_date) == filters["month_number"],
        )
    return query.order_by(OD.applied_on.desc()).all()


def csv_response_content(rows, filters):
    output = io.StringIO()
    writer = csv.writer(output)

    if filters["request_type"] == "leave":
        writer.writerow(
            [
                "ID",
                "Applicant",
                "Department",
                "Class",
                "Start Date",
                "End Date",
                "Reason",
                "Status",
                "Emergency",
                "Proof Uploaded",
                "Applied On",
            ]
        )
        for leave in rows:
            class_label = (
                f"Year {leave.requester.class_group.year} {leave.requester.class_group.section}"
                if leave.requester and leave.requester.class_group
                else "-"
            )
            writer.writerow(
                [
                    leave.id,
                    leave.requester.full_name or leave.requester.username,
                    leave.requester.department.name if leave.requester and leave.requester.department else "-",
                    class_label,
                    leave.start_date.isoformat(),
                    leave.end_date.isoformat(),
                    leave.reason,
                    leave.status,
                    "Yes" if leave.is_emergency else "No",
                    "Yes" if leave.proof_filename else "No",
                    leave.applied_on.strftime("%Y-%m-%d %H:%M"),
                ]
            )
    else:
        writer.writerow(
            [
                "ID",
                "Applicant",
                "Department",
                "Class",
                "Event Date",
                "Reason",
                "Status",
                "Proof Uploaded",
                "Applied On",
            ]
        )
        for od in rows:
            class_label = (
                f"Year {od.requester.class_group.year} {od.requester.class_group.section}"
                if od.requester and od.requester.class_group
                else "-"
            )
            writer.writerow(
                [
                    od.id,
                    od.requester.full_name or od.requester.username,
                    od.requester.department.name if od.requester and od.requester.department else "-",
                    class_label,
                    od.event_date.isoformat(),
                    od.reason,
                    od.status,
                    "Yes" if od.proof_filename else "No",
                    od.applied_on.strftime("%Y-%m-%d %H:%M"),
                ]
            )

    return output.getvalue()


def _escape_pdf_text(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_response_content(rows, filters):
    title = f"{filters['request_type'].upper()} Report"
    lines = [title]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(
        f"Filters -> Department: {filters['department_id'] or 'All'}, Class: {filters['class_group_id'] or 'All'}, Status: {filters['status'] or 'All'}, Month: {filters['month'] or 'All'}"
    )
    lines.append("")

    if filters["request_type"] == "leave":
        for leave in rows[:40]:
            lines.append(
                f"#{leave.id} | {leave.requester.full_name or leave.requester.username} | {leave.start_date} to {leave.end_date} | {leave.status} | Emergency: {'Yes' if leave.is_emergency else 'No'}"
            )
    else:
        for od in rows[:40]:
            lines.append(
                f"#{od.id} | {od.requester.full_name or od.requester.username} | {od.event_date} | {od.status} | Proof: {'Yes' if od.proof_filename else 'No'}"
            )

    if len(rows) > 40:
        lines.append(f"... truncated {len(rows) - 40} additional row(s)")

    content_stream = ["BT", "/F1 10 Tf", "50 790 Td"]
    for index, line in enumerate(lines):
        escaped = _escape_pdf_text(line)
        if index == 0:
            content_stream.append(f"({escaped}) Tj")
        else:
            content_stream.append("0 -14 Td")
            content_stream.append(f"({escaped}) Tj")
    content_stream.append("ET")
    content = "\n".join(content_stream).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj")
    objects.append(b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj")
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")
    objects.append(
        f"5 0 obj << /Length {len(content)} >> stream\n".encode("latin-1") + content + b"\nendstream endobj"
    )

    pdf = io.BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(pdf.tell())
        pdf.write(obj + b"\n")
    xref_offset = pdf.tell()
    pdf.write(f"xref\n0 {len(offsets)}\n".encode("latin-1"))
    pdf.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.write(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1")
    )
    return pdf.getvalue()


def report_context(args):
    filters = build_report_filters(args)
    rows = query_report_rows(filters)
    departments = Department.query.order_by(Department.name.asc()).all()
    classes = ClassGroup.query.order_by(ClassGroup.department_id, ClassGroup.year, ClassGroup.section).all()
    return filters, rows, departments, classes
