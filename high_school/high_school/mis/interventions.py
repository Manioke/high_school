import frappe

from frappe import _


MANAGER_ROLES = ("Education Manager", "System Manager")
OPEN_STATUSES = ("Open", "Meeting Scheduled", "Monitoring")


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

