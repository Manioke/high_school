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


def instructor_teaches_assessment_plan(
    assessment_plan,
    user=None,
):
    user = user or frappe.session.user
    instructor = get_instructor(user)

    if not instructor or not assessment_plan:
        return False

    plan = frappe.db.get_value(
        "Assessment Plan",
        assessment_plan,
        ["course", "student_group"],
        as_dict=True,
    )

    if not plan or not plan.course or not plan.student_group:
        return False

    return bool(
        frappe.db.exists(
            "Course Schedule",
            {
                "course": plan.course,
                "student_group": plan.student_group,
                "instructor": instructor,
            },
        )
    )


def assessment_plan_query(user=None):
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
            WHERE schedule.course =
                `tabAssessment Plan`.`course`
            AND schedule.student_group =
                `tabAssessment Plan`.`student_group`
            AND schedule.instructor =
                {frappe.db.escape(instructor)}
        )
    """


def assessment_result_query(user=None):
    user = user or frappe.session.user

    if not is_instructor_user(user):
        return ""

    instructor = get_instructor(user)

    if not instructor:
        return "1 = 0"

    return f"""
        EXISTS (
            SELECT 1
            FROM `tabAssessment Plan` plan
            INNER JOIN `tabCourse Schedule` schedule
                ON schedule.course = plan.course
                AND schedule.student_group = plan.student_group
            WHERE plan.name =
                `tabAssessment Result`.`assessment_plan`
            AND schedule.instructor =
                {frappe.db.escape(instructor)}
        )
    """


def assessment_plan_has_permission(
    doc,
    user=None,
    permission_type=None,
):
    user = user or frappe.session.user

    if not is_instructor_user(user):
        return None

    if permission_type not in {
        "read",
        "select",
        "print",
    }:
        return False

    instructor = get_instructor(user)

    if not instructor:
        return False

    if not doc.course or not doc.student_group:
        return False

    schedule = frappe.db.get_value(
        "Course Schedule",
        {
            "course": doc.course,
            "student_group": doc.student_group,
            "instructor": instructor,
        },
        "name",
    )

    return bool(schedule)


def assessment_result_has_permission(
    doc,
    user=None,
    permission_type=None,
):
    user = user or frappe.session.user

    if not is_instructor_user(user):
        return None

    if permission_type not in {
        "read",
        "select",
        "create",
        "write",
        "submit",
        "print",
    }:
        return False

    return instructor_teaches_assessment_plan(
        doc.assessment_plan,
        user,
    )


def validate_assessment_result(doc, method=None):
    user = frappe.session.user

    if not is_instructor_user(user):
        return

    if not get_instructor(user):
        frappe.throw(
            _("Your user account is not connected to an Instructor."),
            frappe.PermissionError,
        )

    if not doc.assessment_plan:
        frappe.throw(
            _("An Assessment Plan is required."),
            frappe.PermissionError,
        )

    if not instructor_teaches_assessment_plan(
        doc.assessment_plan,
        user,
    ):
        frappe.throw(
            _(
                "You can only enter results for a course and "
                "student group assigned to you in Course Schedule."
            ),
            frappe.PermissionError,
        )