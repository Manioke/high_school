import json
from urllib.parse import unquote

import frappe
from frappe import _
from frappe.utils import getdate

from high_school.high_school.attendance_utils import (
    mark_standard_attendance,
    mark_taliui_attendance_records,
)
from high_school.high_school.fee_utils import generate_custom_fees
from frappe.desk.calendar import get_event_conditions

from high_school.api.permissions import (
    get_instructor,
    is_instructor_user,
    instructor_teaches_assessment_plan,
)


# ---------------------------------------------------------------------------
# TALIUI / BOARDING ATTENDANCE
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_taliui_records(house, date, taliui):
    """Return students in a house with their attendance status for a Taliui shift."""

    students = frappe.get_all(
        "Student",
        fields=["name as student", "student_name"],
        filters={
            "custom_falemohe": house,
            "enabled": 1,
        },
        order_by="student_name",
    )

    existing_attendance = frappe.get_all(
        "Taliui Akonofo",
        filters={
            "house": house,
            "date": date,
            "taliui": taliui,
        },
        fields=["student", "status"],
    )

    attendance_by_student = {
        row.student: row.status for row in existing_attendance
    }

    for student in students:
        # Default status
        student.status = attendance_by_student.get(student.student, "Absent")

        # Approved leave overrides attendance
        on_leave = frappe.db.exists(
            "Student Leave Application",
            {
                "student": student.student,
                "start_date": ["<=", date],
                "end_date": [">=", date],
                "docstatus": 1,
            },
        )

        if on_leave:
            student.status = "Leave"

    return students


@frappe.whitelist()
def mark_taliui_attendance(
    students_present,
    students_absent,
    house,
    taliui,
    date,
):
    """Create or update Taliui attendance records."""

    present = json.loads(students_present)
    absent = json.loads(students_absent)

    mark_taliui_attendance_records(
        present + absent,
        house=house,
        taliui=taliui,
        date=date,
    )

    return True


# ---------------------------------------------------------------------------
# STUDENT GROUP / OPTION GROUP
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_students_custom(*args, **kwargs):
    """
    Return students for either:

    1. Custom High School option groups (Opt1-Opt4)
    2. Standard Frappe Education student groups
    """

    request_data = frappe._dict(
        kwargs if kwargs else frappe.local.form_dict
    )

    identifier = (
        request_data.get("student_group")
        or request_data.get("student_group_name")
    )

    if not identifier:
        referrer = frappe.local.request.referrer or ""

        if "student-group/" in referrer:
            identifier = (
                referrer
                .split("student-group/")[-1]
                .split("?")[0]
            )

    if not identifier:
        frappe.throw(_("Student Group is required."))

    identifier = unquote(str(identifier))

    option_field_map = {
        "Opt1": "custom_option_1",
        "Opt2": "custom_option_2",
        "Opt3": "custom_option_3",
        "Opt4": "custom_option_4",
    }

    option_field_name = next(
        (
            field_name
            for option_name, field_name in option_field_map.items()
            if option_name in identifier
        ),
        None,
    )

    # -----------------------------------------------------------------------
    # CUSTOM OPTION GROUP
    # -----------------------------------------------------------------------

    if option_field_name:
        student = frappe.qb.DocType("Student")
        program_enrollment = frappe.qb.DocType("Program Enrollment")

        option_field = getattr(student, option_field_name)

        query = (
            frappe.qb.from_(program_enrollment)
            .join(student)
            .on(program_enrollment.student == student.name)
            .select(
                program_enrollment.student,
                program_enrollment.student_name,
            )
            .where(
                program_enrollment.academic_year
                == request_data.get("academic_year")
            )
            .where(program_enrollment.docstatus == 1)
            .where(option_field == request_data.get("course"))
        )

        if request_data.get("program"):
            query = query.where(
                program_enrollment.program
                == request_data.get("program")
            )

        if request_data.get("batch"):
            query = query.where(
                program_enrollment.student_batch_name
                == request_data.get("batch")
            )

        students = query.run(as_dict=True)

        for student_row in students:
            student_row.active = int(
                frappe.db.get_value(
                    "Student",
                    student_row.student,
                    "enabled",
                )
                or 0
            )

        return students

    # -----------------------------------------------------------------------
    # STANDARD FRAPPE EDUCATION GROUP
    # -----------------------------------------------------------------------

    from education.education.doctype.student_group.student_group import (
        get_students,
    )

    return get_students(
        academic_year=request_data.get("academic_year"),
        group_based_on=request_data.get("group_based_on"),
        academic_term=request_data.get("academic_term"),
        program=request_data.get("program"),
        batch=request_data.get("batch"),
        student_category=request_data.get("student_category"),
        course=request_data.get("course"),
    )


# ---------------------------------------------------------------------------
# STANDARD ATTENDANCE API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def custom_mark_attendance(
    students_present,
    students_absent,
    course_schedule=None,
    student_group=None,
    date=None,
):
    """Mark standard Student Attendance using High School rules."""

    present = json.loads(students_present)
    absent = json.loads(students_absent)

    for student in present:
        mark_standard_attendance(
            student=student["student"],
            student_name=student["student_name"],
            status="Present",
            course_schedule=course_schedule,
            student_group=student_group,
            date=date,
        )

    for student in absent:
        mark_standard_attendance(
            student=student["student"],
            student_name=student["student_name"],
            status="Absent",
            course_schedule=course_schedule,
            student_group=student_group,
            date=date,
        )

    frappe.db.commit()

    frappe.msgprint(
        _("Attendance has been marked successfully.")
    )

    return True


# ---------------------------------------------------------------------------
# FEE API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_student_fees(student_enrollment):
    """
    Public API wrapper for custom fee generation.

    The actual fee logic lives in fee_utils.py.
    """

    doc = frappe.get_doc(
        "Program Enrollment",
        student_enrollment,
    )

    return generate_custom_fees(doc)


## Permission API for Course Schedule Calendar
@frappe.whitelist()
def get_course_schedule_events(start, end, filters=None):
    """Return permitted Course Schedule events for the calendar."""

    if not frappe.has_permission("Course Schedule", "read"):
        frappe.throw(
            "You do not have permission to view Course Schedules.",
            frappe.PermissionError,
        )

    conditions = get_event_conditions(
        "Course Schedule",
        filters,
    )

    values = {
        "start": start,
        "end": end,
    }

    instructor_condition = ""

    if is_instructor_user(frappe.session.user):
        instructor = get_instructor(frappe.session.user)

        # Instructor account is not linked correctly.
        if not instructor:
            return []

        values["instructor"] = instructor

        instructor_condition = """
            AND `tabCourse Schedule`.`instructor`
                = %(instructor)s
        """

    return frappe.db.sql(
        f"""
        SELECT
            name,
            course,
            color,
            TIMESTAMP(schedule_date, from_time) AS from_time,
            TIMESTAMP(schedule_date, to_time) AS to_time,
            room,
            student_group,
            instructor,
            0 AS allDay
        FROM `tabCourse Schedule`
        WHERE schedule_date BETWEEN %(start)s AND %(end)s
        {conditions}
        {instructor_condition}
        ORDER BY schedule_date, from_time
        """,
        values,
        as_dict=True,
        update={"allDay": 0},
    )

def check_assessment_plan_access(assessment_plan):
    if not assessment_plan:
        frappe.throw(
            _("Assessment Plan is required."),
            frappe.ValidationError,
        )

    if not frappe.db.exists(
        "Assessment Plan",
        assessment_plan,
    ):
        frappe.throw(
            _("Assessment Plan {0} does not exist.").format(
                assessment_plan
            ),
            frappe.DoesNotExistError,
        )

    user = frappe.session.user

    # Instructors are checked through Course Schedule ownership.
    if is_instructor_user(user):
        if not instructor_teaches_assessment_plan(
            assessment_plan,
            user,
        ):
            frappe.throw(
                _(
                    "You can only enter results for a course and "
                    "student group assigned to you in Course Schedule."
                ),
                frappe.PermissionError,
            )

        # get_doc itself does not perform check_permission().
        return frappe.get_doc(
            "Assessment Plan",
            assessment_plan,
        )

    # Managers and other users use standard Frappe permissions.
    plan = frappe.get_doc(
        "Assessment Plan",
        assessment_plan,
    )

    plan.check_permission("read")

    return plan

@frappe.whitelist()
def get_assessment_students(assessment_plan, student_group):
    check_assessment_plan_access(assessment_plan)

    from education.education.api import (
        get_assessment_students as standard_method,
    )

    return standard_method(
        assessment_plan,
        student_group,
    )


@frappe.whitelist()
def mark_assessment_result(assessment_plan, scores):
    check_assessment_plan_access(assessment_plan)

    from education.education.api import (
        mark_assessment_result as standard_method,
    )

    return standard_method(
        assessment_plan,
        scores,
    )


@frappe.whitelist()
def submit_assessment_results(
    assessment_plan,
    student_group,
):
    check_assessment_plan_access(assessment_plan)

    from education.education.api import (
        submit_assessment_results as standard_method,
    )

    return standard_method(
        assessment_plan,
        student_group,
    )