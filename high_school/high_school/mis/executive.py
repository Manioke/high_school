from high_school.high_school.mis.settings import (
    get_mis_settings,
)

from high_school.high_school.mis.school_term import (
    get_school_term,
)

from high_school.high_school.mis.attendance import (
    DAILY_ATTENDANCE,
    COURSE_ATTENDANCE,
    analyse_attendance,
)

from high_school.high_school.mis.course_attendance import (
    get_course_attendance_sessions,
    get_course_coverage_summary,
    get_teacher_submission_compliance,
)

from high_school.high_school.mis.persistent_absence import (
    get_student_absence_analysis,
)

from high_school.high_school.mis.academic import (
    get_academic_mis,
)

from high_school.high_school.mis.finance import (
    get_financial_mis,
)

from high_school.high_school.mis.direction import (
    get_school_direction,
)

from high_school.high_school.mis.alerts import (
    evaluate_alert_rules,
)


CLOSED_ISSUE_STATUSES = {
    "Resolved",
    "Dismissed",
}


# =========================================================
# Executive MIS
# =========================================================

def get_executive_summary(
    school_term=None,
):
    """
    Build structured Executive MIS data.

    No HTML is generated here.
    """

    # =====================================================
    # Settings
    # =====================================================

    settings = (
        get_mis_settings()
    )

    # =====================================================
    # School Term
    # =====================================================

    term = get_school_term(
        school_term
    )

    if not term:

        return {
            "error":
                "No School Term could be determined."
        }

    start_date = (
        term.start_date
    )

    end_date = (
        term.end_date
    )

    # =====================================================
    # Daily Attendance
    # =====================================================

    daily_attendance = {
        "enabled":
            False,
    }

    if settings[
        "track_daily_attendance"
    ]:

        daily_attendance = {
            "enabled":
                True,

            **analyse_attendance(
                start_date=start_date,
                end_date=end_date,

                attendance_type=(
                    DAILY_ATTENDANCE
                ),

                settings=settings,
            ),
        }

    # =====================================================
    # Course Attendance
    # =====================================================

    course_attendance = {
        "enabled":
            False,
    }

    if settings[
        "track_course_attendance"
    ]:

        performance = (
            analyse_attendance(
                start_date=start_date,
                end_date=end_date,

                attendance_type=(
                    COURSE_ATTENDANCE
                ),

                settings=settings,
            )
        )

        sessions = (
            get_course_attendance_sessions(
                start_date=start_date,
                end_date=end_date,

                coverage_target=settings[
                    "attendance_coverage_target"
                ],

                school_term=term.name,
            )
        )

        coverage = (
            get_course_coverage_summary(
                sessions=sessions,

                coverage_target=settings[
                    "attendance_coverage_target"
                ],
            )
        )

        submission = (
            get_teacher_submission_compliance(
                sessions=sessions,

                submission_target=settings[
                    "attendance_submission_target"
                ],
            )
        )

        attention_sessions = []

        for session in sessions:

            if (
                session[
                    "submission_status"
                ]
                not in (
                    "missing",
                    "incomplete",
                    "data_issue",
                )
            ):

                continue

            issue = (
                session.get(
                    "management_issue"
                )
                or {}
            )

            if (
                issue.get(
                    "status"
                )
                in CLOSED_ISSUE_STATUSES
            ):

                continue

            attention_sessions.append(
                session
            )

        course_attendance = {
            "enabled":
                True,

            "performance":
                performance,

            "coverage":
                coverage,

            "submission":
                submission,

            "session_count":
                len(
                    sessions
                ),

            "attention_sessions":
                attention_sessions[:20],
        }

    # =====================================================
    # Persistent Absence
    # =====================================================

    persistent_absence = {
        "daily": {
            "enabled":
                False,
        },

        "course": {
            "enabled":
                False,
        },

        "unique_students_flagged":
            0,
    }

    if settings[
        "track_daily_attendance"
    ]:

        daily_persistent = (
            get_student_absence_analysis(
                start_date=start_date,
                end_date=end_date,

                attendance_type=(
                    DAILY_ATTENDANCE
                ),

                settings=settings,
            )
        )

        persistent_absence[
            "daily"
        ] = {
            "enabled":
                True,

            **daily_persistent,
        }

    if settings[
        "track_course_attendance"
    ]:

        course_persistent = (
            get_student_absence_analysis(
                start_date=start_date,
                end_date=end_date,

                attendance_type=(
                    COURSE_ATTENDANCE
                ),

                settings=settings,
            )
        )

        persistent_absence[
            "course"
        ] = {
            "enabled":
                True,

            **course_persistent,
        }

    flagged_student_ids = set()

    for mode in (
        "daily",
        "course",
    ):

        mode_data = (
            persistent_absence[
                mode
            ]
        )

        if not mode_data.get(
            "enabled"
        ):

            continue

        for student in mode_data.get(
            "flagged_students",
            [],
        ):

            flagged_student_ids.add(
                student[
                    "student"
                ]
            )

    persistent_absence[
        "unique_students_flagged"
    ] = len(
        flagged_student_ids
    )

    # =====================================================
    # Academic Operations + Performance
    # =====================================================

    academics = (
        get_academic_mis(
            school_term=term.name,
            settings=settings,
        )
    )

    # =====================================================
    # Student Finance
    # =====================================================

    finance = get_financial_mis(
        term=term,
        settings=settings,
    )

    # =====================================================
    # Executive Payload
    # =====================================================

    result = {
        "school_term": {
            "name":
                term.name,

            "academic_year":
                term.academic_year,

            "term":
                term.term,

            "start_date":
                str(
                    term.start_date
                ),

            "end_date":
                str(
                    term.end_date
                ),
        },

        "settings":
            settings,

        "attendance": {
            "daily":
                daily_attendance,

            "course":
                course_attendance,
        },

        "persistent_absence":
            persistent_absence,

        "academics":
            academics,

        "finance":
            finance,
    }

    # =====================================================
    # School Direction
    # =====================================================

    result["direction"] = get_school_direction(
        term=term,
        current_data=result,
        settings=settings,
    )

    # =====================================================
    # Dynamic Alert Rules
    # =====================================================

    result[
        "alerts"
    ] = evaluate_alert_rules(
        data=result,
        settings=settings,
    )

    return result
