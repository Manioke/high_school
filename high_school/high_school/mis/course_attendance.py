import frappe

from frappe.utils import (
    add_days,
    getdate,
    today,
)

from high_school.high_school.mis.issues import (
    CLOSED_STATUSES,
    get_course_attendance_issue_map,
)


# =========================================================
# Course Attendance Sessions
# =========================================================

def get_course_attendance_sessions(
    start_date,
    end_date,
    coverage_target,
    school_term=None,
):
    """
    Analyse expected versus recorded attendance for
    each historical Course Schedule.
    """

    start_date = getdate(
        start_date
    )

    end_date = getdate(
        end_date
    )

    yesterday = add_days(
        getdate(today()),
        -1,
    )

    cutoff_date = min(
        end_date,
        yesterday,
    )

    if cutoff_date < start_date:
        return []

    # =====================================================
    # Course Schedules
    # =====================================================

    schedules = frappe.get_all(
        "Course Schedule",

        filters={
            "schedule_date": [
                "between",
                [
                    start_date,
                    cutoff_date,
                ],
            ],
        },

        fields=[
            "name",
            "student_group",

            "instructor",
            "instructor_name",

            "course",
            "program",

            "schedule_date",

            "from_time",
            "to_time",

            "room",
        ],

        order_by=(
            "schedule_date asc, "
            "from_time asc"
        ),
    )

    if not schedules:
        return []

    # =====================================================
    # Expected students
    # =====================================================

    group_names = list({
        schedule.student_group

        for schedule
        in schedules

        if schedule.student_group
    })

    expected_by_group = {}

    if group_names:

        rows = frappe.db.sql(
            """
            SELECT
                parent AS student_group,

                COUNT(
                    DISTINCT student
                ) AS expected_students

            FROM `tabStudent Group Student`

            WHERE
                parent IN %(groups)s

                AND active = 1

            GROUP BY
                parent
            """,

            {
                "groups":
                    tuple(group_names)
            },

            as_dict=True,
        )

        expected_by_group = {
            row.student_group:
                int(
                    row.expected_students
                    or 0
                )

            for row in rows
        }

    # =====================================================
    # Attendance records
    # =====================================================

    schedule_names = [
        schedule.name
        for schedule in schedules
    ]

    rows = frappe.db.sql(
        """
        SELECT
            course_schedule,

            COUNT(
                DISTINCT student
            ) AS recorded_students,

            SUM(
                CASE
                    WHEN status = 'Present'
                    THEN 1
                    ELSE 0
                END
            ) AS present_count,

            SUM(
                CASE
                    WHEN status = 'Absent'
                    THEN 1
                    ELSE 0
                END
            ) AS absent_count,

            SUM(
                CASE
                    WHEN status = 'Leave'
                    THEN 1
                    ELSE 0
                END
            ) AS leave_count

        FROM `tabStudent Attendance`

        WHERE
            course_schedule IN %(schedules)s

            AND course_schedule IS NOT NULL

            AND course_schedule != ''

            AND docstatus < 2

        GROUP BY
            course_schedule
        """,

        {
            "schedules":
                tuple(schedule_names)
        },

        as_dict=True,
    )

    attendance_by_schedule = {
        row.course_schedule:
            row

        for row in rows
    }

    # =====================================================
    # Existing management issues
    # =====================================================

    issue_map = (
        get_course_attendance_issue_map(
            course_schedule_names=
                schedule_names,

            school_term=
                school_term,
        )
    )

    # =====================================================
    # Build session output
    # =====================================================

    output = []

    for schedule in schedules:

        expected = (
            expected_by_group.get(
                schedule.student_group,
                0,
            )
        )

        attendance = (
            attendance_by_schedule.get(
                schedule.name
            )
        )

        recorded = (
            int(
                attendance.recorded_students
                or 0
            )
            if attendance
            else 0
        )

        present = (
            int(
                attendance.present_count
                or 0
            )
            if attendance
            else 0
        )

        absent = (
            int(
                attendance.absent_count
                or 0
            )
            if attendance
            else 0
        )

        leave = (
            int(
                attendance.leave_count
                or 0
            )
            if attendance
            else 0
        )

        # =================================================
        # Coverage
        # =================================================

        coverage_rate = (
            round(
                (
                    recorded
                    / expected
                )
                * 100,
                1,
            )
            if expected
            else None
        )

        # =================================================
        # Student attendance performance
        # =================================================

        counted = (
            present
            + absent
        )

        attendance_rate = (
            round(
                (
                    present
                    / counted
                )
                * 100,
                1,
            )
            if counted
            else None
        )

        # =================================================
        # Submission status
        # =================================================

        if expected == 0:

            submission_status = (
                "no_students"
            )

        elif recorded == 0:

            submission_status = (
                "missing"
            )

        elif (
            coverage_rate is not None
            and coverage_rate > 100
        ):

            submission_status = (
                "data_issue"
            )

        elif (
            coverage_rate
            >= coverage_target
        ):

            submission_status = (
                "complete"
            )

        else:

            submission_status = (
                "incomplete"
            )

        output.append({
            "course_schedule":
                schedule.name,

            "course":
                schedule.course,

            "student_group":
                schedule.student_group,

            "instructor":
                schedule.instructor,

            "instructor_name":
                schedule.instructor_name,

            "schedule_date":
                str(
                    schedule.schedule_date
                ),

            "from_time":
                (
                    str(schedule.from_time)
                    if schedule.from_time
                    else None
                ),

            "to_time":
                (
                    str(schedule.to_time)
                    if schedule.to_time
                    else None
                ),

            "room":
                schedule.room,

            "expected_students":
                expected,

            "recorded_students":
                recorded,

            "coverage_rate":
                coverage_rate,

            "attendance_rate":
                attendance_rate,

            "present":
                present,

            "absent":
                absent,

            "leave":
                leave,

            "submission_status":
                submission_status,

            "management_issue":
                issue_map.get(
                    schedule.name
                ),
        })

    return output


# =========================================================
# Management Helpers
# =========================================================

def _is_resolved(
    session,
):
    issue = (
        session.get(
            "management_issue"
        )
        or {}
    )

    return (
        issue.get(
            "status"
        )
        in CLOSED_STATUSES
    )


def _exclude_from_kpis(
    session,
):
    issue = (
        session.get(
            "management_issue"
        )
        or {}
    )

    return (
        _is_resolved(
            session
        )
        and
        bool(
            issue.get(
                "exclude_from_kpis"
            )
        )
    )


# =========================================================
# Course Coverage
# =========================================================

def get_course_coverage_summary(
    sessions,
    coverage_target,
):
    """
    Calculate Course Attendance coverage.

    Approved resolved issues marked Exclude from KPI
    Calculations are excluded from this denominator.
    """

    expected = 0
    recorded = 0

    data_issue_sessions = 0
    no_student_sessions = 0
    management_excluded_sessions = 0

    for session in sessions:

        if _exclude_from_kpis(
            session
        ):

            management_excluded_sessions += 1
            continue

        status = (
            session[
                "submission_status"
            ]
        )

        if status == "no_students":

            no_student_sessions += 1
            continue

        if status == "data_issue":

            data_issue_sessions += 1
            continue

        expected += (
            session[
                "expected_students"
            ]
        )

        recorded += (
            session[
                "recorded_students"
            ]
        )

    coverage_rate = (
        round(
            (
                recorded
                / expected
            )
            * 100,
            1,
        )
        if expected
        else None
    )

    if coverage_rate is None:

        status = "no_data"

    elif (
        coverage_rate
        < coverage_target
    ):

        status = "warning"

    else:

        status = "healthy"

    return {
        "coverage_rate":
            coverage_rate,

        "target":
            coverage_target,

        "status":
            status,

        "expected_records":
            expected,

        "recorded_records":
            recorded,

        "data_issue_sessions":
            data_issue_sessions,

        "no_student_sessions":
            no_student_sessions,

        "management_excluded_sessions":
            management_excluded_sessions,
    }


# =========================================================
# Teacher Submission Compliance
# =========================================================

def get_teacher_submission_compliance(
    sessions,
    submission_target,
):
    """
    Calculate Course Attendance submission compliance.

    Resolved issues disappear from actionable counts.

    A resolved issue only disappears from KPI
    calculations when Exclude from KPI Calculations
    was explicitly selected.
    """

    teachers = {}

    overall_expected = 0
    overall_complete = 0

    overall_missing = 0
    overall_incomplete = 0

    actionable_missing = 0
    actionable_incomplete = 0

    resolved_sessions = 0

    excluded_sessions = 0
    management_excluded_sessions = 0

    unassigned_sessions = 0

    for session in sessions:

        status = (
            session[
                "submission_status"
            ]
        )

        resolved = (
            _is_resolved(
                session
            )
        )

        if resolved:
            resolved_sessions += 1

        # ---------------------------------------------
        # Management exclusion
        # ---------------------------------------------

        if _exclude_from_kpis(
            session
        ):

            excluded_sessions += 1

            management_excluded_sessions += 1

            continue

        # ---------------------------------------------
        # Technically non-assessable
        # ---------------------------------------------

        if status in (
            "no_students",
            "data_issue",
        ):

            excluded_sessions += 1

            continue

        overall_expected += 1

        if status == "complete":

            overall_complete += 1

        elif status == "missing":

            overall_missing += 1

            if not resolved:
                actionable_missing += 1

        elif status == "incomplete":

            overall_incomplete += 1

            if not resolved:
                actionable_incomplete += 1

        instructor = (
            session[
                "instructor"
            ]
        )

        if not instructor:

            unassigned_sessions += 1
            continue

        instructor_name = (
            session[
                "instructor_name"
            ]
            or instructor
        )

        if instructor not in teachers:

            teachers[
                instructor
            ] = {
                "instructor":
                    instructor,

                "instructor_name":
                    instructor_name,

                "expected_sessions":
                    0,

                "complete_sessions":
                    0,

                "missing_sessions":
                    0,

                "incomplete_sessions":
                    0,
            }

        teacher = (
            teachers[
                instructor
            ]
        )

        teacher[
            "expected_sessions"
        ] += 1

        if status == "complete":

            teacher[
                "complete_sessions"
            ] += 1

        elif status == "missing":

            teacher[
                "missing_sessions"
            ] += 1

        elif status == "incomplete":

            teacher[
                "incomplete_sessions"
            ] += 1

    # =====================================================
    # Teacher rates
    # =====================================================

    teacher_results = []

    for teacher in teachers.values():

        expected = (
            teacher[
                "expected_sessions"
            ]
        )

        complete = (
            teacher[
                "complete_sessions"
            ]
        )

        compliance_rate = (
            round(
                (
                    complete
                    / expected
                )
                * 100,
                1,
            )
            if expected
            else None
        )

        teacher[
            "compliance_rate"
        ] = compliance_rate

        teacher[
            "target"
        ] = submission_target

        if compliance_rate is None:

            teacher[
                "status"
            ] = "no_data"

        elif (
            compliance_rate
            < submission_target
        ):

            teacher[
                "status"
            ] = "warning"

        else:

            teacher[
                "status"
            ] = "healthy"

        teacher_results.append(
            teacher
        )

    teacher_results.sort(
        key=lambda item: (
            item[
                "compliance_rate"
            ] is None,

            item[
                "compliance_rate"
            ]
            if item[
                "compliance_rate"
            ] is not None
            else 999,
        )
    )

    # =====================================================
    # Overall
    # =====================================================

    overall_rate = (
        round(
            (
                overall_complete
                / overall_expected
            )
            * 100,
            1,
        )
        if overall_expected
        else None
    )

    if overall_rate is None:

        overall_status = (
            "no_data"
        )

    elif (
        overall_rate
        < submission_target
    ):

        overall_status = (
            "warning"
        )

    else:

        overall_status = (
            "healthy"
        )

    teachers_below_target = [
        teacher

        for teacher
        in teacher_results

        if (
            teacher[
                "compliance_rate"
            ] is not None

            and

            teacher[
                "compliance_rate"
            ]
            < submission_target
        )
    ]

    return {
        "compliance_rate":
            overall_rate,

        "target":
            submission_target,

        "status":
            overall_status,

        "expected_sessions":
            overall_expected,

        "complete_sessions":
            overall_complete,

        # Historical KPI failures
        "missing_sessions":
            overall_missing,

        "incomplete_sessions":
            overall_incomplete,

        # Still requiring management attention
        "actionable_missing_sessions":
            actionable_missing,

        "actionable_incomplete_sessions":
            actionable_incomplete,

        "resolved_sessions":
            resolved_sessions,

        "excluded_sessions":
            excluded_sessions,

        "management_excluded_sessions":
            management_excluded_sessions,

        "unassigned_sessions":
            unassigned_sessions,

        "teachers_below_target":
            len(
                teachers_below_target
            ),

        "teachers":
            teacher_results,
    }