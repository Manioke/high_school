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

        "restrict_instructor_attendance_to_today": bool(
            settings.get("restrict_instructor_attendance_to_today")
        ),

        "missing_attendance_reminder_threshold": _int_setting(
            settings.get("missing_attendance_reminder_threshold"), 10
        ),

        "attendance_reminder_action": (
            settings.get("attendance_reminder_action") or "Email Reminder"
        ),

        "attendance_insights_dashboard_url": (
            settings.get("attendance_insights_dashboard_url") or ""
        ),

        "assessment_insights_dashboard_url": (
            settings.get("assessment_insights_dashboard_url") or ""
        ),

        "finance_insights_dashboard_url": (
            settings.get("finance_insights_dashboard_url") or ""
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

        "academic_performance_target": _float_setting(
            settings.get("academic_performance_target"), 60
        ),

        "auto_create_academic_interventions": (
            True if settings.get("auto_create_academic_interventions") is None
            else bool(settings.get("auto_create_academic_interventions"))
        ),

        "academic_intervention_threshold": _float_setting(
            settings.get("academic_intervention_threshold"), 50
        ),

        "academic_intervention_standard_deviations": _float_setting(
            settings.get("academic_intervention_standard_deviations"), 1.5
        ),

        "academic_intervention_consecutive_periods": _int_setting(
            settings.get("academic_intervention_consecutive_periods"), 2
        ),

        "auto_create_attendance_interventions": (
            True if settings.get("auto_create_attendance_interventions") is None
            else bool(settings.get("auto_create_attendance_interventions"))
        ),

        "course_attendance_absence_trigger_count": _int_setting(
            settings.get("course_attendance_absence_trigger_count"), 3
        ),

        "course_attendance_escalation_absence_count": _int_setting(
            settings.get("course_attendance_escalation_absence_count"), 3
        ),

        "send_intervention_email_notifications": (
            True if settings.get("send_intervention_email_notifications") is None
            else bool(settings.get("send_intervention_email_notifications"))
        ),

        "intervention_follow_up_days": _int_setting(
            settings.get("intervention_follow_up_days"), 21
        ),

        "default_intervention_owner": settings.get("default_intervention_owner"),
        "school_principal_user": settings.get("school_principal_user"),
        "school_counselor_user": settings.get("school_counselor_user"),

        # =================================================
        # Whole-school Finance and Student Fees
        # =================================================

        "track_school_finance": (
            True
            if settings.get("track_school_finance") is None
            else bool(settings.get("track_school_finance"))
        ),

        "finance_company": settings.get("finance_company"),

        "finance_cost_center": settings.get("finance_cost_center"),

        "student_fee_income_account": settings.get(
            "student_fee_income_account"
        ),

        "wage_expense_account": settings.get("wage_expense_account"),

        "track_hr_payroll": (
            True
            if settings.get("track_hr_payroll") is None
            else bool(settings.get("track_hr_payroll"))
        ),

        "payroll_payable_account": settings.get("payroll_payable_account"),

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
