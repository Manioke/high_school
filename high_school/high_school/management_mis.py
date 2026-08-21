import frappe

from high_school.high_school.mis.settings import (
    get_mis_settings,
)

from high_school.high_school.mis.course_attendance import (
    get_course_attendance_sessions,
)

from high_school.high_school.mis.issues import (
    create_or_get_issue,
    mark_under_review,
    resolve_issue as resolve_mis_issue,
    reopen_issue as reopen_mis_issue,
)


# =========================================================
# Course Attendance Issue
# =========================================================

@frappe.whitelist()
def get_or_create_course_attendance_issue(
    course_schedule,
    school_term=None,
):
    """
    Create or retrieve a management issue for a
    problematic historical Course Schedule.
    """

    settings = (
        get_mis_settings()
    )

    schedule = frappe.get_doc(
        "Course Schedule",
        course_schedule,
    )

    # Calculate this one scheduled class using the
    # same logic as the Executive MIS.
    sessions = (
        get_course_attendance_sessions(
            start_date=schedule.schedule_date,
            end_date=schedule.schedule_date,

            coverage_target=settings[
                "attendance_coverage_target"
            ],

            school_term=school_term,
        )
    )

    session = next(
        (
            item

            for item
            in sessions

            if (
                item[
                    "course_schedule"
                ]
                == course_schedule
            )
        ),
        None,
    )

    if not session:

        frappe.throw(
            "This Course Schedule cannot currently "
            "be managed as an attendance exception. "
            "Only completed historical sessions are "
            "included."
        )

    status = (
        session[
            "submission_status"
        ]
    )

    if status == "complete":

        frappe.throw(
            "Attendance for this scheduled class "
            "is already complete."
        )

    issue_type_map = {
        "missing":
            "Missing Course Attendance",

        "incomplete":
            "Incomplete Course Attendance",

        "data_issue":
            "Course Attendance Data Issue",

        "no_students":
            "Course Schedule Has No Active Students",
    }

    issue_type = (
        issue_type_map.get(
            status,
            "Course Attendance Issue",
        )
    )

    coverage = (
        session[
            "coverage_rate"
        ]
    )

    coverage_text = (
        f"{coverage}%"
        if coverage is not None
        else "N/A"
    )

    description = (
        f"{session['course']} on "
        f"{session['schedule_date']} for "
        f"{session['student_group']}: "
        f"{session['recorded_students']} of "
        f"{session['expected_students']} expected "
        f"student attendance records were found "
        f"(coverage {coverage_text})."
    )

    return create_or_get_issue(
        source_type="Attendance",

        issue_type=issue_type,

        title=(
            f"{issue_type}: "
            f"{session['course']}"
        ),

        severity="Warning",

        description=description,

        reference_doctype=(
            "Course Schedule"
        ),

        reference_name=(
            course_schedule
        ),

        school_term=(
            school_term
        ),

        instructor=(
            session[
                "instructor"
            ]
        ),
    )


# =========================================================
# Issue Actions
# =========================================================

@frappe.whitelist()
def mark_issue_under_review(
    issue_name,
):
    return mark_under_review(
        issue_name
    )


@frappe.whitelist()
def resolve_issue(
    issue_name,
    resolution_type,
    resolution_notes=None,
    exclude_from_kpis=0,
):
    return resolve_mis_issue(
        issue_name=issue_name,

        resolution_type=
            resolution_type,

        resolution_notes=
            resolution_notes,

        exclude_from_kpis=
            exclude_from_kpis,
    )


@frappe.whitelist()
def reopen_issue(
    issue_name,
):
    return reopen_mis_issue(
        issue_name
    )