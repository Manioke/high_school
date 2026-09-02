import frappe

from frappe import _


MANAGER_ROLES = ("Education Manager", "System Manager")
OPEN_STATUSES = ("Open", "Meeting Scheduled", "Monitoring")
CLOSED_STATUSES = ("Resolved", "Dismissed")


def apply_attendance_interventions(persistent_absence, school_term):
    """Hide a resolved risk until later attendance creates new evidence."""
    rows = frappe.get_all(
        "Student Attendance Intervention",
        filters={"school_term": school_term},
        fields=[
            "name", "student", "attendance_type", "status",
            "attendance_records", "resolved_attendance_records", "resolved_on",
        ],
        order_by="modified desc",
    )
    latest = {}
    for row in rows:
        latest.setdefault((row.student, row.attendance_type), row)

    managed = []
    for mode, attendance_type in (("daily", "Daily"), ("course", "Course")):
        mode_data = persistent_absence.get(mode) or {}
        if not mode_data.get("enabled"):
            continue

        actionable = []
        for student in mode_data.get("flagged_students") or []:
            case = latest.get((student.get("student"), attendance_type))
            if case:
                student["intervention"] = {
                    "name": case.name,
                    "status": case.status,
                }

            baseline = 0
            if case and case.status in CLOSED_STATUSES:
                baseline = int(
                    case.resolved_attendance_records
                    or case.attendance_records
                    or 0
                )
            if baseline and int(student.get("counted_records") or 0) <= baseline:
                managed.append({
                    **student,
                    "attendance_type": attendance_type,
                    "intervention": student.get("intervention"),
                })
                continue
            actionable.append(student)

        mode_data["raw_persistent_absence_count"] = mode_data.get(
            "persistent_absence_count", len(mode_data.get("flagged_students") or [])
        )
        mode_data["flagged_students"] = actionable
        mode_data["persistent_absence_count"] = len(actionable)

    unique_students = {
        row.get("student")
        for mode in ("daily", "course")
        for row in (persistent_absence.get(mode) or {}).get("flagged_students", [])
        if row.get("student")
    }
    persistent_absence["unique_students_flagged"] = len(unique_students)
    persistent_absence["managed_students"] = managed
    persistent_absence["managed_students_count"] = len({
        row.get("student") for row in managed if row.get("student")
    })
    return persistent_absence


@frappe.whitelist()
def get_or_create_attendance_intervention(
    student,
    school_term,
    attendance_type,
    absence_rate=None,
    attendance_records=None,
):
    frappe.only_for(MANAGER_ROLES)

    normalized_type = (attendance_type or "").strip().title()
    if normalized_type not in {"Daily", "Course"}:
        frappe.throw(_("Attendance Type must be Daily or Course."))

    if not frappe.db.exists("Student", student):
        frappe.throw(_("Student {0} does not exist.").format(student))
    if not frappe.db.exists("School Term", school_term):
        frappe.throw(_("School Term {0} does not exist.").format(school_term))

    existing = frappe.db.get_value(
        "Student Attendance Intervention",
        {
            "student": student,
            "school_term": school_term,
            "attendance_type": normalized_type,
            "status": ["in", OPEN_STATUSES],
        },
    )

    if existing:
        doc = frappe.get_doc("Student Attendance Intervention", existing)
        if absence_rate is not None:
            doc.absence_rate = absence_rate
        if attendance_records is not None:
            doc.attendance_records = attendance_records
        doc.save()
        return {"name": doc.name, "created": False}

    doc = frappe.new_doc("Student Attendance Intervention")
    doc.update(
        {
            "student": student,
            "school_term": school_term,
            "attendance_type": normalized_type,
            "absence_rate": absence_rate,
            "attendance_records": attendance_records,
            "status": "Open",
            "assigned_to": frappe.session.user,
        }
    )
    doc.insert()
    return {"name": doc.name, "created": True}
