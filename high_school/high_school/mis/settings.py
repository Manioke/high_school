import frappe


def _float_setting(value, default):
    """
    Return a Float setting while preserving a valid
    configured value of 0.
    """

    if value is None or value == "":
        return float(default)

    return float(value)


def _int_setting(value, default):
    """
    Return an Int setting while preserving a valid
    configured value of 0.
    """

    if value is None or value == "":
        return int(default)

    return int(value)


def get_mis_settings():
    """
    Return the school's MIS configuration.
    """

    settings = frappe.get_single(
        "School MIS Settings"
    )

    return {
        "attendance_target":
            _float_setting(
                settings.attendance_target,
                90,
            ),

        "attendance_coverage_target":
            _float_setting(
                settings.attendance_coverage_target,
                95,
            ),

        "attendance_submission_target":
            _float_setting(
                settings.attendance_submission_target,
                95,
            ),

        "persistent_absence_threshold":
            _float_setting(
                settings.persistent_absence_threshold,
                10,
            ),

        "minimum_group_attendance_records":
            _int_setting(
                settings.minimum_group_attendance_records,
                10,
            ),

        "minimum_student_attendance_records":
            _int_setting(
                settings.minimum_student_attendance_records,
                10,
            ),

        "track_daily_attendance":
            bool(
                settings.track_daily_attendance
            ),

        "track_course_attendance":
            bool(
                settings.track_course_attendance
            ),
    }