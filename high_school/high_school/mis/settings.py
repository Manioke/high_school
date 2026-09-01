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
    Return the school's Executive MIS configuration.
    """

    settings = frappe.get_single(
        "School MIS Settings"
    )

    return {
        # =================================================
        # Attendance
        # =================================================

        "attendance_target":
            _float_setting(
                settings.get(
                    "attendance_target"
                ),
                90,
            ),

        "attendance_coverage_target":
            _float_setting(
                settings.get(
                    "attendance_coverage_target"
                ),
                95,
            ),

        "attendance_submission_target":
            _float_setting(
                settings.get(
                    "attendance_submission_target"
                ),
                95,
            ),

        "persistent_absence_threshold":
            _float_setting(
                settings.get(
                    "persistent_absence_threshold"
                ),
                10,
            ),

        "minimum_group_attendance_records":
            _int_setting(
                settings.get(
                    "minimum_group_attendance_records"
                ),
                10,
            ),

        "minimum_student_attendance_records":
            _int_setting(
                settings.get(
                    "minimum_student_attendance_records"
                ),
                10,
            ),

        "track_daily_attendance":
            bool(
                settings.get(
                    "track_daily_attendance"
                )
            ),

        "track_course_attendance":
            bool(
                settings.get(
                    "track_course_attendance"
                )
            ),

        # =================================================
        # Academic Operations
        # =================================================

        "exam_preparation_target":
            _float_setting(
                settings.get(
                    "exam_preparation_target"
                ),
                95,
            ),

        "assessment_plan_coverage_target":
            _float_setting(
                settings.get(
                    "assessment_plan_coverage_target"
                ),
                100,
            ),

        "assessment_result_submission_target":
            _float_setting(
                settings.get(
                    "assessment_result_submission_target"
                ),
                95,
            ),

        # =================================================
        # Student Finance
        # =================================================

        "track_student_finance":
            (
                True
                if settings.get(
                    "track_student_finance"
                ) is None
                else bool(
                    settings.get(
                        "track_student_finance"
                    )
                )
            ),

        "fee_collection_target":
            _float_setting(
                settings.get(
                    "fee_collection_target"
                ),
                90,
            ),

        "overdue_fee_target":
            _float_setting(
                settings.get(
                    "overdue_fee_target"
                ),
                5,
            ),
    }
