import operator

import frappe


# =========================================================
# Operators
# =========================================================

OPERATORS = {
    "<":
        operator.lt,

    "<=":
        operator.le,

    ">":
        operator.gt,

    ">=":
        operator.ge,

    "==":
        operator.eq,
}


# =========================================================
# Supported MIS Settings
# =========================================================

SETTING_ALIASES = {
    "attendance_target":
        "attendance_target",

    "Attendance Target":
        "attendance_target",

    "attendance_coverage_target":
        "attendance_coverage_target",

    "Attendance Coverage Target":
        "attendance_coverage_target",

    "attendance_submission_target":
        "attendance_submission_target",

    "Attendance Submission Target":
        "attendance_submission_target",

    "persistent_absence_threshold":
        "persistent_absence_threshold",

    "Persistent Absence Threshold":
        "persistent_absence_threshold",

    "minimum_group_attendance_records":
        "minimum_group_attendance_records",

    "Minimum Group Attendance Records":
        "minimum_group_attendance_records",

    "minimum_student_attendance_records":
        "minimum_student_attendance_records",

    "Minimum Student Attendance Records":
        "minimum_student_attendance_records",
}


# =========================================================
# Threshold
# =========================================================

def get_rule_threshold(
    rule,
    settings,
):
    """
    Resolve the configured threshold for an alert rule.
    """

    source = (
        rule.threshold_source
        or ""
    ).strip()

    # =====================================================
    # MIS Settings
    # =====================================================

    if source == "MIS Settings":

        setting_key = (
            SETTING_ALIASES.get(
                rule.threshold_setting
            )
        )

        if not setting_key:

            return None

        value = settings.get(
            setting_key
        )

        if value is None:

            return None

        return float(
            value
        )

    # =====================================================
    # Custom Value
    # =====================================================

    if source == "Custom Value":

        if (
            rule.custom_threshold
            is None
        ):

            return None

        return float(
            rule.custom_threshold
        )

    return None


# =========================================================
# Compare
# =========================================================

def rule_matches(
    value,
    comparison_operator,
    threshold,
):
    """
    Compare a metric value against its configured
    threshold.
    """

    if value is None:

        return False

    compare = OPERATORS.get(
        comparison_operator
    )

    if not compare:

        return False

    return compare(
        float(value),
        float(threshold),
    )


# =========================================================
# Candidate Helper
# =========================================================

def _candidate(
    value,
    subject,
    context=None,
    **extra,
):
    """
    Build a normalized MIS metric candidate.
    """

    return {
        "value":
            value,

        "subject":
            subject,

        "context":
            context,

        **extra,
    }


# =========================================================
# Metric Resolution
# =========================================================

def get_metric_candidates(
    rule,
    data,
    settings,
):
    """
    Resolve values represented by an MIS Alert Rule.

    Daily and Course attendance are never
    mathematically combined.
    """

    metric = (
        rule.metric
    )

    scope = (
        rule.scope
    )

    attendance = (
        data.get(
            "attendance",
            {},
        )
    )

    daily = (
        attendance.get(
            "daily",
            {},
        )
    )

    course = (
        attendance.get(
            "course",
            {},
        )
    )

    persistent_absence = (
        data.get(
            "persistent_absence",
            {},
        )
    )

    candidates = []

    # =====================================================
    # Overall
    # =====================================================

    if scope == "Overall":

        # -------------------------------------------------
        # Attendance Rate
        # -------------------------------------------------

        if metric == "Attendance Rate":

            if daily.get(
                "enabled"
            ):

                summary = daily.get(
                    "summary",
                    {},
                )

                candidates.append(
                    _candidate(
                        value=summary.get(
                            "attendance_rate"
                        ),

                        subject=(
                            "Daily Attendance"
                        ),

                        context="daily",
                    )
                )

            if course.get(
                "enabled"
            ):

                summary = (
                    course
                    .get(
                        "performance",
                        {},
                    )
                    .get(
                        "summary",
                        {},
                    )
                )

                candidates.append(
                    _candidate(
                        value=summary.get(
                            "attendance_rate"
                        ),

                        subject=(
                            "Course Attendance"
                        ),

                        context="course",
                    )
                )

        # -------------------------------------------------
        # Attendance Coverage
        # -------------------------------------------------

        elif (
            metric
            == "Attendance Coverage"
        ):

            if course.get(
                "enabled"
            ):

                coverage = (
                    course.get(
                        "coverage",
                        {},
                    )
                )

                candidates.append(
                    _candidate(
                        value=coverage.get(
                            "coverage_rate"
                        ),

                        subject=(
                            "Course Attendance Coverage"
                        ),

                        context="course",
                    )
                )

        # -------------------------------------------------
        # Submission Compliance
        # -------------------------------------------------

        elif (
            metric
            == "Attendance Submission Compliance"
        ):

            if course.get(
                "enabled"
            ):

                submission = (
                    course.get(
                        "submission",
                        {},
                    )
                )

                candidates.append(
                    _candidate(
                        value=submission.get(
                            "compliance_rate"
                        ),

                        subject=(
                            "Course Attendance Submission"
                        ),

                        context="course",
                    )
                )

        # -------------------------------------------------
        # Missing Sessions
        # -------------------------------------------------

        elif (
            metric
            == "Missing Attendance Sessions"
        ):

            if course.get(
                "enabled"
            ):

                submission = (
                    course.get(
                        "submission",
                        {},
                    )
                )

                candidates.append(
                    _candidate(
                        value=submission.get(
                            "missing_sessions"
                        ),

                        subject=(
                            "Missing Course Attendance"
                        ),

                        context="course",
                    )
                )

        # -------------------------------------------------
        # Teachers Below Target
        # -------------------------------------------------

        elif (
            metric
            == "Teachers Below Submission Target"
        ):

            if course.get(
                "enabled"
            ):

                submission = (
                    course.get(
                        "submission",
                        {},
                    )
                )

                candidates.append(
                    _candidate(
                        value=submission.get(
                            "teachers_below_target"
                        ),

                        subject=(
                            "Instructor Attendance "
                            "Compliance"
                        ),

                        context="course",
                    )
                )

        # -------------------------------------------------
        # Persistent Absence Student Count
        # -------------------------------------------------

        elif (
            metric
            == "Persistent Absence Students"
        ):

            candidates.append(
                _candidate(
                    value=(
                        persistent_absence.get(
                            "unique_students_flagged",
                            0,
                        )
                    ),

                    subject=(
                        "Students with Persistent Absence"
                    ),

                    context="student",
                )
            )

        return candidates

    # =====================================================
    # Daily Attendance
    # =====================================================

    if scope == "Daily Attendance":

        if not daily.get(
            "enabled"
        ):

            return []

        summary = daily.get(
            "summary",
            {},
        )

        if metric == "Attendance Rate":

            candidates.append(
                _candidate(
                    value=summary.get(
                        "attendance_rate"
                    ),

                    subject=(
                        "Daily Attendance"
                    ),

                    context="daily",
                )
            )

        return candidates

    # =====================================================
    # Course Attendance
    # =====================================================

    if scope == "Course Attendance":

        if not course.get(
            "enabled"
        ):

            return []

        performance = (
            course
            .get(
                "performance",
                {},
            )
            .get(
                "summary",
                {},
            )
        )

        coverage = (
            course.get(
                "coverage",
                {},
            )
        )

        submission = (
            course.get(
                "submission",
                {},
            )
        )

        if metric == "Attendance Rate":

            candidates.append(
                _candidate(
                    value=performance.get(
                        "attendance_rate"
                    ),

                    subject=(
                        "Course Attendance"
                    ),

                    context="course",
                )
            )

        elif (
            metric
            == "Attendance Coverage"
        ):

            candidates.append(
                _candidate(
                    value=coverage.get(
                        "coverage_rate"
                    ),

                    subject=(
                        "Course Attendance Coverage"
                    ),

                    context="course",
                )
            )

        elif (
            metric
            == "Attendance Submission Compliance"
        ):

            candidates.append(
                _candidate(
                    value=submission.get(
                        "compliance_rate"
                    ),

                    subject=(
                        "Course Attendance Submission"
                    ),

                    context="course",
                )
            )

        elif (
            metric
            == "Missing Attendance Sessions"
        ):

            candidates.append(
                _candidate(
                    value=submission.get(
                        "missing_sessions"
                    ),

                    subject=(
                        "Missing Course Attendance"
                    ),

                    context="course",
                )
            )

        elif (
            metric
            == "Teachers Below Submission Target"
        ):

            candidates.append(
                _candidate(
                    value=submission.get(
                        "teachers_below_target"
                    ),

                    subject=(
                        "Instructor Attendance "
                        "Compliance"
                    ),

                    context="course",
                )
            )

        return candidates

    # =====================================================
    # Student Group
    # =====================================================

    if scope == "Student Group":

        if metric != "Attendance Rate":

            return []

        minimum_records = (
            settings.get(
                "minimum_group_attendance_records",
                0,
            )
        )

        # -------------------------------------------------
        # Daily
        # -------------------------------------------------

        if daily.get(
            "enabled"
        ):

            for group in daily.get(
                "groups",
                [],
            ):

                if (
                    group.get(
                        "counted_records",
                        0,
                    )
                    < minimum_records
                ):

                    continue

                candidates.append(
                    _candidate(
                        value=group.get(
                            "attendance_rate"
                        ),

                        subject=group.get(
                            "student_group"
                        ),

                        context="daily",

                        student_group=group.get(
                            "student_group"
                        ),
                    )
                )

        # -------------------------------------------------
        # Course
        # -------------------------------------------------

        if course.get(
            "enabled"
        ):

            performance = (
                course.get(
                    "performance",
                    {},
                )
            )

            for group in performance.get(
                "groups",
                [],
            ):

                if (
                    group.get(
                        "counted_records",
                        0,
                    )
                    < minimum_records
                ):

                    continue

                candidates.append(
                    _candidate(
                        value=group.get(
                            "attendance_rate"
                        ),

                        subject=group.get(
                            "student_group"
                        ),

                        context="course",

                        student_group=group.get(
                            "student_group"
                        ),
                    )
                )

        return candidates

    # =====================================================
    # Instructor
    # =====================================================

    if scope == "Instructor":

        if not course.get(
            "enabled"
        ):

            return []

        if (
            metric
            != "Attendance Submission Compliance"
        ):

            return []

        submission = course.get(
            "submission",
            {},
        )

        for teacher in submission.get(
            "teachers",
            [],
        ):

            instructor = teacher.get(
                "instructor"
            )

            candidates.append(
                _candidate(
                    value=teacher.get(
                        "compliance_rate"
                    ),

                    subject=(
                        teacher.get(
                            "instructor_name"
                        )

                        or

                        instructor

                        or

                        "Unknown Instructor"
                    ),

                    context="course",

                    instructor=instructor,

                    expected_sessions=teacher.get(
                        "expected_sessions"
                    ),

                    complete_sessions=teacher.get(
                        "complete_sessions"
                    ),

                    missing_sessions=teacher.get(
                        "missing_sessions"
                    ),

                    incomplete_sessions=teacher.get(
                        "incomplete_sessions"
                    ),
                )
            )

        return candidates

    # =====================================================
    # Student
    # =====================================================

    if scope == "Student":

        if (
            metric
            != "Persistent Absence Rate"
        ):

            return []

        for mode in (
            "daily",
            "course",
        ):

            mode_data = (
                persistent_absence.get(
                    mode,
                    {},
                )
            )

            if not mode_data.get(
                "enabled"
            ):

                continue

            for student in mode_data.get(
                "students",
                [],
            ):

                if not student.get(
                    "enough_data"
                ):

                    continue

                candidates.append(
                    _candidate(
                        value=student.get(
                            "absence_rate"
                        ),

                        subject=(
                            student.get(
                                "student_name"
                            )

                            or

                            student.get(
                                "student"
                            )
                        ),

                        context=mode,

                        student=student.get(
                            "student"
                        ),

                        present=student.get(
                            "present"
                        ),

                        absent=student.get(
                            "absent"
                        ),

                        leave=student.get(
                            "leave"
                        ),

                        counted_records=student.get(
                            "counted_records"
                        ),
                    )
                )

        return candidates

    return []


# =========================================================
# Evaluate Alert Rules
# =========================================================

def evaluate_alert_rules(
    data,
    settings,
):
    """
    Evaluate enabled MIS Alert Rules.

    Returns structured alert data only.
    """

    rules = frappe.get_all(
        "MIS Alert Rule",

        filters={
            "enabled": 1,
        },

        fields=[
            "name",
            "rule_name",

            "metric",
            "scope",

            "operator",

            "threshold_source",
            "threshold_setting",
            "custom_threshold",

            "severity",

            "alert_title",
            "message",
            "recommended_action",
        ],

        order_by="creation asc",
    )

    alerts = []

    for row in rules:

        rule = frappe._dict(
            row
        )

        threshold = (
            get_rule_threshold(
                rule=rule,
                settings=settings,
            )
        )

        if threshold is None:

            continue

        candidates = (
            get_metric_candidates(
                rule=rule,
                data=data,
                settings=settings,
            )
        )

        for candidate in candidates:

            value = (
                candidate.get(
                    "value"
                )
            )

            if not rule_matches(
                value=value,
                comparison_operator=(
                    rule.operator
                ),
                threshold=threshold,
            ):

                continue

            alert = {
                "rule":
                    rule.name,

                "rule_name":
                    rule.rule_name,

                "title":
                    (
                        rule.alert_title

                        or

                        rule.rule_name

                        or

                        rule.name
                    ),

                "metric":
                    rule.metric,

                "scope":
                    rule.scope,

                "severity":
                    (
                        rule.severity
                        or "Warning"
                    ),

                "value":
                    value,

                "operator":
                    rule.operator,

                "threshold":
                    threshold,

                "message":
                    (
                        rule.message
                        or ""
                    ),

                "recommended_action":
                    (
                        rule.recommended_action
                        or ""
                    ),

                "subject":
                    candidate.get(
                        "subject"
                    ),

                "context":
                    candidate.get(
                        "context"
                    ),
            }

            for fieldname in (
                "student_group",
                "instructor",
                "student",

                "present",
                "absent",
                "leave",
                "counted_records",

                "expected_sessions",
                "complete_sessions",
                "missing_sessions",
                "incomplete_sessions",
            ):

                if (
                    fieldname
                    in candidate
                ):

                    alert[
                        fieldname
                    ] = candidate[
                        fieldname
                    ]

            alerts.append(
                alert
            )

    # =====================================================
    # Severity Ordering
    # =====================================================

    severity_priority = {
        "Critical":
            0,

        "Action Required":
            1,

        "Warning":
            2,

        "Information":
            3,
    }

    alerts.sort(
        key=lambda alert: (
            severity_priority.get(
                alert[
                    "severity"
                ],
                99,
            ),

            alert.get(
                "title"
            )
            or "",
        )
    )

    return alerts