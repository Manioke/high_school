import frappe


DAILY_ATTENDANCE = "daily"
COURSE_ATTENDANCE = "course"


# =========================================================
# Attendance Type
# =========================================================

def _attendance_condition(
    attendance_type,
):
    """
    Separate daily attendance from
    Course Schedule attendance.
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
# Persistent Absence Analysis
# =========================================================

def get_student_absence_analysis(
    start_date,
    end_date,
    attendance_type,
    settings,
):
    """
    Calculate absence rate per student.

    Absence Rate =
        Absent / (Present + Absent) * 100

    Leave is excluded.

    Students are not considered persistently absent
    until they meet the school's configured minimum
    number of counted attendance records.
    """

    condition = (
        _attendance_condition(
            attendance_type
        )
    )

    rows = frappe.db.sql(
        f"""
        SELECT
            student,

            MAX(
                student_name
            ) AS student_name,

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

        FROM
            `tabStudent Attendance`

        WHERE
            date BETWEEN
                %(start_date)s
                AND %(end_date)s

            AND student IS NOT NULL

            AND student != ''

            AND {condition}

            AND docstatus < 2

        GROUP BY
            student
        """,

        {
            "start_date":
                start_date,

            "end_date":
                end_date,
        },

        as_dict=True,
    )

    threshold = float(
        settings[
            "persistent_absence_threshold"
        ]
    )

    minimum_records = int(
        settings[
            "minimum_student_attendance_records"
        ]
    )

    students = []

    flagged = []

    insufficient_data = []

    for row in rows:

        present = int(
            row.present_count or 0
        )

        absent = int(
            row.absent_count or 0
        )

        leave = int(
            row.leave_count or 0
        )

        counted = (
            present
            + absent
        )

        absence_rate = (
            round(
                (
                    absent
                    / counted
                )
                * 100,
                1,
            )
            if counted
            else None
        )

        enough_data = (
            counted
            >= minimum_records
        )

        persistent_absence = (
            enough_data

            and

            absence_rate is not None

            and

            absence_rate
            >= threshold
        )

        student = {
            "student":
                row.student,

            "student_name":
                row.student_name,

            "present":
                present,

            "absent":
                absent,

            "leave":
                leave,

            "counted_records":
                counted,

            "absence_rate":
                absence_rate,

            "threshold":
                threshold,

            "enough_data":
                enough_data,

            "persistent_absence":
                persistent_absence,
        }

        students.append(
            student
        )

        if persistent_absence:

            flagged.append(
                student
            )

        elif not enough_data:

            insufficient_data.append(
                student
            )

    # =====================================================
    # Sort
    # =====================================================

    students.sort(
        key=lambda item: (
            item[
                "absence_rate"
            ] is None,

            -item[
                "absence_rate"
            ]
            if item[
                "absence_rate"
            ] is not None
            else 0,
        )
    )

    flagged.sort(
        key=lambda item:
            -item[
                "absence_rate"
            ]
    )

    return {
        "type":
            attendance_type,

        "threshold":
            threshold,

        "minimum_records":
            minimum_records,

        "students_analysed":
            len(
                students
            ),

        "persistent_absence_count":
            len(
                flagged
            ),

        "insufficient_data_count":
            len(
                insufficient_data
            ),

        "flagged_students":
            flagged,

        # Retained for future detailed MIS analysis.
        "students":
            students,
    }