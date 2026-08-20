import frappe


DAILY_ATTENDANCE = "daily"
COURSE_ATTENDANCE = "course"


# =========================================================
# Attendance Type
# =========================================================

def _get_attendance_condition(
    attendance_type,
):
    """
    Return the SQL condition used to separate
    daily attendance from Course Schedule attendance.
    """

    if attendance_type == DAILY_ATTENDANCE:

        return """
            (
                course_schedule IS NULL
                OR course_schedule = ''
            )
        """

    if attendance_type == COURSE_ATTENDANCE:

        return """
            (
                course_schedule IS NOT NULL
                AND course_schedule != ''
            )
        """

    frappe.throw(
        f"Invalid attendance type: {attendance_type}"
    )


# =========================================================
# Overall Attendance
# =========================================================

def get_attendance_summary(
    start_date,
    end_date,
    attendance_type,
):
    """
    Calculate attendance statistics for a period.

    Attendance Rate =
        Present / (Present + Absent) * 100

    Leave is deliberately excluded.
    """

    attendance_condition = (
        _get_attendance_condition(
            attendance_type
        )
    )

    result = frappe.db.sql(
        f"""
        SELECT

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
            date BETWEEN
                %(start_date)s
                AND %(end_date)s

            AND {attendance_condition}

            AND docstatus < 2
        """,

        {
            "start_date":
                start_date,

            "end_date":
                end_date,
        },

        as_dict=True,
    )[0]

    present = int(
        result.present_count or 0
    )

    absent = int(
        result.absent_count or 0
    )

    leave = int(
        result.leave_count or 0
    )

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

    return {
        "present":
            present,

        "absent":
            absent,

        "leave":
            leave,

        "counted_records":
            counted,

        "attendance_rate":
            attendance_rate,
    }


# =========================================================
# Student Group Attendance
# =========================================================

def get_group_attendance(
    start_date,
    end_date,
    attendance_type,
):
    """
    Calculate attendance statistics for each
    Student Group.
    """

    attendance_condition = (
        _get_attendance_condition(
            attendance_type
        )
    )

    groups = frappe.db.sql(
        f"""
        SELECT
            student_group,

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
            date BETWEEN
                %(start_date)s
                AND %(end_date)s

            AND student_group IS NOT NULL

            AND student_group != ''

            AND {attendance_condition}

            AND docstatus < 2

        GROUP BY
            student_group
        """,

        {
            "start_date":
                start_date,

            "end_date":
                end_date,
        },

        as_dict=True,
    )

    output = []

    for group in groups:

        present = int(
            group.present_count or 0
        )

        absent = int(
            group.absent_count or 0
        )

        leave = int(
            group.leave_count or 0
        )

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

        output.append({
            "student_group":
                group.student_group,

            "attendance_rate":
                attendance_rate,

            "present":
                present,

            "absent":
                absent,

            "leave":
                leave,

            "counted_records":
                counted,
        })

    # Lowest reliable attendance first.
    # No-data groups last.

    output.sort(
        key=lambda item: (
            item[
                "attendance_rate"
            ] is None,

            item[
                "attendance_rate"
            ]
            if item[
                "attendance_rate"
            ] is not None
            else 999,
        )
    )

    return output


# =========================================================
# Attendance Analysis
# =========================================================

def analyse_attendance(
    start_date,
    end_date,
    attendance_type,
    settings,
):
    """
    Analyse attendance and return structured MIS data.

    No HTML or presentation logic is generated here.
    """

    attendance_target = (
        settings[
            "attendance_target"
        ]
    )

    minimum_records = (
        settings[
            "minimum_group_attendance_records"
        ]
    )

    summary = get_attendance_summary(
        start_date=start_date,
        end_date=end_date,
        attendance_type=attendance_type,
    )

    groups = get_group_attendance(
        start_date=start_date,
        end_date=end_date,
        attendance_type=attendance_type,
    )

    groups_below_target = []

    groups_with_insufficient_data = []

    for group in groups:

        # ---------------------------------------------
        # Not enough data
        # ---------------------------------------------

        if (
            group["counted_records"]
            < minimum_records
        ):

            groups_with_insufficient_data.append(
                group
            )

            continue

        # ---------------------------------------------
        # Below attendance target
        # ---------------------------------------------

        if (
            group["attendance_rate"]
            is not None

            and

            group["attendance_rate"]
            < attendance_target
        ):

            groups_below_target.append(
                group
            )

    # =====================================================
    # Lowest reliable group
    # =====================================================

    lowest_group = None

    for group in groups:

        if (
            group["attendance_rate"]
            is not None

            and

            group["counted_records"]
            >= minimum_records
        ):

            lowest_group = group

            break

    # =====================================================
    # Overall status
    # =====================================================

    attendance_rate = (
        summary[
            "attendance_rate"
        ]
    )

    if attendance_rate is None:

        status = "no_data"

    elif (
        attendance_rate
        < attendance_target
    ):

        status = "warning"

    else:

        status = "healthy"

    summary["target"] = (
        attendance_target
    )

    summary["status"] = status

    return {
        "type":
            attendance_type,

        "summary":
            summary,

        "analysis": {
            "lowest_group":
                lowest_group,

            "groups_below_target":
                groups_below_target,

            "groups_below_target_count":
                len(
                    groups_below_target
                ),

            "groups_with_insufficient_data":
                groups_with_insufficient_data,

            "groups_with_insufficient_data_count":
                len(
                    groups_with_insufficient_data
                ),
        },

        "groups":
            groups,
    }
