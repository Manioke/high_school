import frappe
from frappe.utils import getdate, today


# =========================================================
# Executive MIS Configuration
# =========================================================

def get_mis_settings():
    """
    Return the school's Executive MIS configuration.

    School MIS Settins is a Single DocType, so there is
    only one configuration record for the school.
    """

    settings = frappe.get_single("School MIS Settings")

    return {
        "attendance_target": float(
            settings.attendance_target or 90
        ),

        "attendance_submission_target": float(
            settings.attendance_submission_target or 95
        ),

        "persistent_absence_target": float(
            settings.persistent_absence_threshold or 10
        ),

        "minimum_group_attendance_records": int(
            settings.minimum_group_attendance_records or 10
        ),
    }


# =========================================================
# School Term
# =========================================================

def get_current_school_term():
    """Return the School Term containing today's date."""

    current_date = getdate(today())

    terms = frappe.get_all(
        "School Term",
        filters={
            "start_date": ["<=", current_date],
            "end_date": [">=", current_date],
        },
        fields=[
            "name",
            "academic_year",
            "term",
            "start_date",
            "end_date",
        ],
        order_by="start_date desc",
        limit=1,
    )

    return terms[0] if terms else None


# =========================================================
# Attendance Summary
# =========================================================

def get_attendance_summary(start_date, end_date):
    """Calculate overall attendance statistics for a date range."""

    result = frappe.db.sql(
        """
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

        WHERE date BETWEEN %(start_date)s AND %(end_date)s
        """,
        {
            "start_date": start_date,
            "end_date": end_date,
        },
        as_dict=True,
    )[0]

    present = result.present_count or 0
    absent = result.absent_count or 0
    leave = result.leave_count or 0

    # Leave is deliberately excluded from the
    # attendance percentage calculation.
    counted = present + absent

    if counted:
        attendance_rate = round(
            (present / counted) * 100,
            1,
        )
    else:
        attendance_rate = None

    return {
        "present": present,
        "absent": absent,
        "leave": leave,
        "attendance_rate": attendance_rate,
        "counted_records": counted,
    }


# =========================================================
# Student Group Attendance
# =========================================================

def get_group_attendance(start_date, end_date):
    """Calculate attendance statistics for each Student Group."""

    groups = frappe.db.sql(
        """
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
            date BETWEEN %(start_date)s AND %(end_date)s

            AND student_group IS NOT NULL

            AND student_group != ''

        GROUP BY student_group
        """,
        {
            "start_date": start_date,
            "end_date": end_date,
        },
        as_dict=True,
    )

    output = []

    for group in groups:

        present = group.present_count or 0
        absent = group.absent_count or 0
        leave = group.leave_count or 0

        counted = present + absent

        if counted:
            attendance_rate = round(
                (present / counted) * 100,
                1,
            )
        else:
            attendance_rate = None

        output.append(
            {
                "student_group": group.student_group,
                "attendance_rate": attendance_rate,
                "present": present,
                "absent": absent,
                "leave": leave,
                "counted_records": counted,
            }
        )

    # Put groups with the lowest attendance first.
    # Groups with no attendance data are placed at the end.
    output.sort(
        key=lambda x: (
            x["attendance_rate"] is None,
            x["attendance_rate"]
            if x["attendance_rate"] is not None
            else 999,
        )
    )

    return output


# =========================================================
# Executive Summary
# =========================================================

@frappe.whitelist()
def get_executive_summary(school_term=None):
    """
    Generate the Executive MIS summary.

    If school_term is not supplied, the School Term
    containing today's date is automatically selected.
    """

    # -----------------------------------------------------
    # Load MIS Settings
    # -----------------------------------------------------

    settings = get_mis_settings()

    attendance_target = settings["attendance_target"]

    attendance_submission_target = (
        settings["attendance_submission_target"]
    )

    persistent_absence_target = (
        settings["persistent_absence_target"]
    )

    minimum_group_attendance_records = (
        settings["minimum_group_attendance_records"]
    )

    # -----------------------------------------------------
    # Determine School Term
    # -----------------------------------------------------

    if school_term:

        term = frappe.get_doc(
            "School Term",
            school_term,
        )

    else:

        term = get_current_school_term()

    if not term:

        return {
            "error": "No School Term could be determined."
        }

    # -----------------------------------------------------
    # Attendance
    # -----------------------------------------------------

    attendance = get_attendance_summary(
        term.start_date,
        term.end_date,
    )

    groups = get_group_attendance(
        term.start_date,
        term.end_date,
    )

    # -----------------------------------------------------
    # Identify groups below target
    #
    # The school's attendance target is used for all
    # Student Groups. There is no separate group target.
    #
    # We only consider groups with enough attendance
    # records to make the comparison meaningful.
    # -----------------------------------------------------

    groups_below_target = [
        group
        for group in groups
        if (
            group["attendance_rate"] is not None
            and group["attendance_rate"] < attendance_target
            and group["counted_records"]
            >= minimum_group_attendance_records
        )
    ]

    # -----------------------------------------------------
    # Identify groups with insufficient data
    # -----------------------------------------------------

    groups_with_insufficient_data = [
        group
        for group in groups
        if (
            group["attendance_rate"] is not None
            and group["counted_records"]
            < minimum_group_attendance_records
        )
    ]

    # -----------------------------------------------------
    # Lowest group with enough attendance data
    # -----------------------------------------------------

    lowest_group = None

    for group in groups:

        if (
            group["attendance_rate"] is not None
            and group["counted_records"]
            >= minimum_group_attendance_records
        ):

            lowest_group = group
            break

    # -----------------------------------------------------
    # Determine overall attendance status
    # -----------------------------------------------------

    attendance_rate = attendance["attendance_rate"]

    if attendance_rate is None:

        attendance_status = "no_data"

    elif attendance_rate < attendance_target:

        attendance_status = "warning"

    else:

        attendance_status = "healthy"

    attendance["status"] = attendance_status

    attendance["target"] = attendance_target

    attendance["groups_below_target"] = len(
        groups_below_target
    )

    attendance["groups_with_insufficient_data"] = len(
        groups_with_insufficient_data
    )

    attendance["lowest_group"] = lowest_group

    # -----------------------------------------------------
    # Management Commentary
    # -----------------------------------------------------

    comments = []

    # -----------------------------------------------------
    # No attendance data
    # -----------------------------------------------------

    if attendance_rate is None:

        comments.append(
            f"""
            <li>
                <b>Attendance Data:</b>
                No Present or Absent attendance records
                have been recorded for {term.term} yet.
            </li>
            """
        )

        # Leave records may exist even when there are
        # no Present/Absent records.
        if attendance["leave"] > 0:

            comments.append(
                f"""
                <li>
                    <b>Leave Records:</b>
                    {attendance["leave"]}
                    leave record(s) have been recorded
                    during {term.term}.
                </li>
                """
            )

        comments.append(
            f"""
            <li>
                <b>Recommended Action:</b>
                Confirm that teachers or attendance
                officers are submitting daily attendance
                records for {term.term}.
            </li>
            """
        )

    # -----------------------------------------------------
    # Attendance below target
    # -----------------------------------------------------

    elif attendance_rate < attendance_target:

        comments.append(
            f"""
            <li>
                <b>Attendance Warning:</b>
                Overall attendance for {term.term}
                is {attendance_rate}%,
                below the school target of
                {attendance_target}%.
            </li>
            """
        )

        # Lowest group
        if lowest_group:

            comments.append(
                f"""
                <li>
                    <b>Area Requiring Attention:</b>
                    {lowest_group["student_group"]}
                    has the lowest recorded attendance
                    rate at
                    {lowest_group["attendance_rate"]}%,
                    based on
                    {lowest_group["counted_records"]}
                    attendance records.
                </li>
                """
            )

        # Groups below target
        if groups_below_target:

            comments.append(
                f"""
                <li>
                    <b>Recommended Action:</b>
                    Review the
                    {len(groups_below_target)}
                    Student Group(s) below the
                    {attendance_target}% attendance
                    target and identify persistent
                    absenteeism.
                </li>
                """
            )

        # Groups with insufficient data
        if groups_with_insufficient_data:

            comments.append(
                f"""
                <li>
                    <b>Data Quality Notice:</b>
                    {len(groups_with_insufficient_data)}
                    Student Group(s) have fewer than
                    {minimum_group_attendance_records}
                    counted attendance records and
                    should not be treated as reliable
                    performance comparisons yet.
                </li>
                """
            )

    # -----------------------------------------------------
    # Attendance healthy
    # -----------------------------------------------------

    else:

        comments.append(
            f"""
            <li>
                <b>Attendance Healthy:</b>
                Overall attendance for {term.term}
                is {attendance_rate}%,
                meeting the school target of
                {attendance_target}%.
            </li>
            """
        )

        # There may still be individual groups
        # performing below the overall target.
        if groups_below_target:

            comments.append(
                f"""
                <li>
                    <b>Area Requiring Attention:</b>
                    {len(groups_below_target)}
                    Student Group(s) remain below the
                    {attendance_target}% target.
                </li>
                """
            )

        # Insufficient data
        if groups_with_insufficient_data:

            comments.append(
                f"""
                <li>
                    <b>Data Quality Notice:</b>
                    {len(groups_with_insufficient_data)}
                    Student Group(s) have fewer than
                    {minimum_group_attendance_records}
                    counted attendance records.
                </li>
                """
            )

    # -----------------------------------------------------
    # Summary HTML
    # -----------------------------------------------------

    summary_html = f"""
        <ul>
            {''.join(comments)}
        </ul>
    """

    # -----------------------------------------------------
    # Return Executive MIS data
    # -----------------------------------------------------

    return {
        "school_term": {
            "name": term.name,
            "academic_year": term.academic_year,
            "term": term.term,
            "start_date": str(term.start_date),
            "end_date": str(term.end_date),
        },

        "settings": {
            "attendance_target": attendance_target,
            "attendance_submission_target":
                attendance_submission_target,
            "persistent_absence_target":
                persistent_absence_target,
            "minimum_group_attendance_records":
                minimum_group_attendance_records,
        },

        "attendance": attendance,

        "groups": groups,

        "summary_html": summary_html,
    }