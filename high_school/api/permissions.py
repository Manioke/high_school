import frappe
from frappe import _


PRIVILEGED_ROLES = {
    "Administrator",
    "System Manager",
    "Education Manager",
}


def is_instructor_user(user):
    roles = set(frappe.get_roles(user))
    return "Instructor" in roles and not roles.intersection(PRIVILEGED_ROLES)


def get_instructor(user):
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        "name",
    )

    if not employee:
        return None

    return frappe.db.get_value(
        "Instructor",
        {"employee": employee},
        "name",
    )


def course_schedule_query(user=None):
    user = user or frappe.session.user

    if not is_instructor_user(user):
        return ""

    instructor = get_instructor(user)

    if not instructor:
        return "1 = 0"

    return (
        "`tabCourse Schedule`.`instructor` = "
        + frappe.db.escape(instructor)
    )


def student_attendance_query(user=None):
    user = user or frappe.session.user

    if not is_instructor_user(user):
        return ""

    instructor = get_instructor(user)

    if not instructor:
        return "1 = 0"

    return f"""
        EXISTS (
            SELECT 1
            FROM `tabCourse Schedule` schedule
            WHERE schedule.name =
                `tabStudent Attendance`.`course_schedule`
            AND schedule.instructor =
                {frappe.db.escape(instructor)}
        )
    """


def course_schedule_has_permission(
    doc,
    user=None,
    permission_type=None,
):
    user = user or frappe.session.user

    if not is_instructor_user(user):
        return None

    return doc.instructor == get_instructor(user)


def student_attendance_has_permission(
    doc,
    user=None,
    permission_type=None,
):
    user = user or frappe.session.user

    if not is_instructor_user(user):
        return None

    if not doc.course_schedule:
        return False

    schedule_instructor = frappe.db.get_value(
        "Course Schedule",
        doc.course_schedule,
        "instructor",
    )

    return schedule_instructor == get_instructor(user)


def validate_student_attendance(doc, method=None):
    user = frappe.session.user

    if not is_instructor_user(user):
        return

    instructor = get_instructor(user)

    if not instructor:
        frappe.throw(
            _("Your user account is not connected to an Instructor."),
            frappe.PermissionError,
        )

    if not doc.course_schedule:
        frappe.throw(
            _("Instructors must mark attendance against a Course Schedule."),
            frappe.PermissionError,
        )

    schedule_instructor = frappe.db.get_value(
        "Course Schedule",
        doc.course_schedule,
        "instructor",
    )

    if schedule_instructor != instructor:
        frappe.throw(
            _("You can only mark attendance for your own Course Schedule."),
            frappe.PermissionError,
        )