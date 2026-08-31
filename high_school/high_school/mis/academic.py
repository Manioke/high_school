import frappe

from frappe.utils import (
    getdate,
    nowdate,
)

from high_school.high_school.report.exam_preparation_coverage.exam_preparation_coverage import (
    get_data as get_exam_preparation_rows,
)


# =========================================================
# Constants
# =========================================================

PAPER_READY_STATUSES = {
    "Approved",
    "Plans Partially Created",
    "Complete",
}


EXCLUDED_RESULT_STATUSES = {
    "Plan Cancelled",
}


RESULT_DATA_ISSUE_STATUSES = {
    "Awaiting Plan Submission",
    "Instructor Mapping Error",
}


# =========================================================
# Helpers
# =========================================================

def _percentage(
    numerator,
    denominator,
):
    """
    Return a percentage or None when no denominator
    exists.
    """

    if not denominator:
        return None

    return round(
        (
            numerator
            / denominator
        )
        * 100,
        1,
    )


def _target_status(
    value,
    target,
):
    """
    Return a normalized MIS status.
    """

    if value is None:
        return "no_data"

    if value < target:
        return "warning"

    return "healthy"


# =========================================================
# Examination Cycles
# =========================================================

def get_examination_cycles(
    school_term,
):
    """
    Return all examination cycles belonging to the
    selected School Term.

    Multiple cycles are deliberately supported.
    """

    return frappe.get_all(
        "School Examination Cycle",

        filters={
            "school_term":
                school_term,
        },

        fields=[
            "name",
            "cycle_name",
            "academic_year",
            "school_term",
            "assessment_group",
            "assessment_type",
            "status",

            "exam_start_date",
            "exam_end_date",

            "assignment_deadline",
            "paper_submission_deadline",
            "hod_review_deadline",
            "admin_approval_deadline",

            "result_deadline_basis",
            "result_turnaround_days",
            "fixed_result_deadline",
        ],

        order_by=(
            "exam_start_date asc, "
            "creation asc"
        ),
    )


# =========================================================
# Exam Preparation
# =========================================================

def get_exam_preparation_summary(
    school_term,
    cycles,
    settings,
):
    """
    Aggregate the existing Exam Preparation Coverage
    report into Executive MIS metrics.

    The existing report remains the detailed source.
    This function does not recreate its deadline logic.
    """

    target = float(
        settings[
            "exam_preparation_target"
        ]
    )

    plan_target = float(
        settings[
            "assessment_plan_coverage_target"
        ]
    )

    rows = []

    # =====================================================
    # Reuse existing report logic
    # =====================================================

    for cycle in cycles:

        # A Draft cycle has not yet generated requirements.
        if cycle.status == "Draft":
            continue

        cycle_rows = (
            get_exam_preparation_rows(
                frappe._dict({
                    "examination_cycle":
                        cycle.name,
                })
            )
        )

        for row in cycle_rows:

            item = dict(
                row
            )

            item[
                "examination_cycle"
            ] = cycle.name

            item[
                "cycle_name"
            ] = (
                cycle.cycle_name
                or cycle.name
            )

            rows.append(
                item
            )

    # =====================================================
    # Counts
    # =====================================================

    total_requirements = len(
        rows
    )

    assigned_requirements = 0

    paper_ready_requirements = 0

    fully_ready_requirements = 0

    overdue_requirements = 0

    missing_group_mappings = 0

    expected_plans = 0
    created_plans = 0
    missing_plans = 0

    attention_items = []

    # =====================================================
    # Analyse each requirement
    # =====================================================

    for row in rows:

        reasons = []

        # ---------------------------------------------
        # Teacher assignment
        # ---------------------------------------------

        if row.get(
            "lead_teacher_user"
        ):

            assigned_requirements += 1

        else:

            reasons.append(
                "Lead Teacher Not Assigned"
            )

        # ---------------------------------------------
        # Paper approval/readiness
        # ---------------------------------------------

        paper_ready = (
            row.get(
                "status"
            )
            in PAPER_READY_STATUSES
        )

        if paper_ready:

            paper_ready_requirements += 1

        else:

            reasons.append(
                "Paper Preparation Incomplete"
            )

        # ---------------------------------------------
        # Assessment Plan mapping / creation
        # ---------------------------------------------

        row_expected = int(
            row.get(
                "expected_plans"
            )
            or 0
        )

        row_created = int(
            row.get(
                "created_plans"
            )
            or 0
        )

        row_missing = int(
            row.get(
                "missing_plans"
            )
            or 0
        )

        expected_plans += (
            row_expected
        )

        created_plans += (
            row_created
        )

        missing_plans += (
            row_missing
        )

        if row_expected <= 0:

            missing_group_mappings += 1

            reasons.append(
                "Student Group Mapping Missing"
            )

        elif row_missing > 0:

            reasons.append(
                "Assessment Plans Missing"
            )

        # ---------------------------------------------
        # Fully ready
        # ---------------------------------------------

        fully_ready = (
            paper_ready
            and row_expected > 0
            and row_missing == 0
        )

        if fully_ready:

            fully_ready_requirements += 1

        # ---------------------------------------------
        # Existing report deadline
        # ---------------------------------------------

        days_remaining = (
            row.get(
                "days_remaining"
            )
        )

        overdue = (
            bool(reasons)
            and days_remaining is not None
            and days_remaining < 0
        )

        if overdue:

            overdue_requirements += 1

            reasons.append(
                "Deadline Passed"
            )

        # ---------------------------------------------
        # Attention
        # ---------------------------------------------

        if reasons:

            attention_items.append({
                **row,

                "attention_reasons":
                    reasons,

                "overdue":
                    overdue,
            })

    # =====================================================
    # Rates
    # =====================================================

    assignment_rate = _percentage(
        assigned_requirements,
        total_requirements,
    )

    paper_approval_rate = (
        _percentage(
            paper_ready_requirements,
            total_requirements,
        )
    )

    preparation_coverage_rate = (
        _percentage(
            fully_ready_requirements,
            total_requirements,
        )
    )

    plan_coverage_rate = (
        _percentage(
            created_plans,
            expected_plans,
        )
    )

    # =====================================================
    # Status
    # =====================================================

    preparation_status = (
        _target_status(
            preparation_coverage_rate,
            target,
        )
    )

    plan_status = (
        _target_status(
            plan_coverage_rate,
            plan_target,
        )
    )

    # Missing mappings are important even when the
    # calculated plan denominator happens to look healthy.
    if (
        missing_group_mappings > 0
        and plan_status == "healthy"
    ):

        plan_status = "warning"

    return {
        "target":
            target,

        "status":
            preparation_status,

        "coverage_rate":
            preparation_coverage_rate,

        "assignment_rate":
            assignment_rate,

        "paper_approval_rate":
            paper_approval_rate,

        "total_requirements":
            total_requirements,

        "assigned_requirements":
            assigned_requirements,

        "paper_ready_requirements":
            paper_ready_requirements,

        "fully_ready_requirements":
            fully_ready_requirements,

        "outstanding_requirements":
            len(
                attention_items
            ),

        "overdue_requirements":
            overdue_requirements,

        "missing_group_mappings":
            missing_group_mappings,

        # ---------------------------------------------
        # Assessment Plan generation
        # ---------------------------------------------

        "assessment_plans": {
            "target":
                plan_target,

            "status":
                plan_status,

            "coverage_rate":
                plan_coverage_rate,

            "expected":
                expected_plans,

            "created":
                created_plans,

            "missing":
                missing_plans,
        },

        # Main Executive page should not receive
        # unlimited operational rows.
        "attention_items":
            attention_items[:50],
    }


# =========================================================
# Assessment Result Submission
# =========================================================

def get_result_submission_summary(
    school_term,
    settings,
):
    """
    Aggregate Assessment Result Submission Tracker
    records.

    Result submission compliance is deadline-aware:
    future assessments do not reduce compliance.
    """

    target = float(
        settings[
            "assessment_result_submission_target"
        ]
    )

    trackers = frappe.get_all(
        "Assessment Result Submission Tracker",

        filters={
            "school_term":
                school_term,
        },

        fields=[
            "name",

            "assessment_plan",
            "status",

            "exam_paper_requirement",
            "examination_cycle",
            "assessment_type",

            "academic_year",
            "school_term",
            "assessment_group",

            "course",
            "student_group",

            "assessment_date",
            "result_due_date",

            "instructor",
            "responsible_user",
            "hod_user",
            "instructor_mapping_issue",

            "expected_student_count",
            "draft_result_count",
            "submitted_result_count",
            "non_participation_count",
            "missing_result_count",
            "completion_percentage",

            "completed_on",
        ],

        order_by=(
            "result_due_date asc, "
            "assessment_date asc"
        ),
    )

    today = getdate(
        nowdate()
    )

    # =====================================================
    # Counters
    # =====================================================

    total_trackers = len(
        trackers
    )

    cancelled_trackers = 0
    future_trackers = 0

    awaiting_plan_submission = 0
    instructor_mapping_errors = 0

    due_trackers = 0
    complete_due_trackers = 0
    outstanding_due_trackers = 0

    expected_students_due = 0
    resolved_students_due = 0
    missing_students_due = 0

    overdue_trackers = 0

    responsible_people = set()

    attention_items = []

    # =====================================================
    # Analyse Trackers
    # =====================================================

    for tracker in trackers:

        status = (
            tracker.status
        )

        # ---------------------------------------------
        # Cancelled
        # ---------------------------------------------

        if (
            status
            in EXCLUDED_RESULT_STATUSES
        ):

            cancelled_trackers += 1

            continue

        # ---------------------------------------------
        # Assessment Plan itself is not submitted
        # ---------------------------------------------

        if (
            status
            == "Awaiting Plan Submission"
        ):

            awaiting_plan_submission += 1

            attention_items.append({
                **tracker,

                "attention_reason":
                    "Assessment Plan Awaiting Submission",

                "overdue":
                    False,
            })

            continue

        # ---------------------------------------------
        # Instructor mapping
        # ---------------------------------------------

        if (
            status
            == "Instructor Mapping Error"
        ):

            instructor_mapping_errors += 1

            attention_items.append({
                **tracker,

                "attention_reason":
                    "Instructor Mapping Error",

                "overdue":
                    False,
            })

            continue

        # ---------------------------------------------
        # Determine whether results are actually due
        #
        # Tracker logic uses:
        # due_date < today => Overdue
        # ---------------------------------------------

        due_date = (
            getdate(
                tracker.result_due_date
            )
            if tracker.result_due_date
            else None
        )

        is_due = (
            due_date is not None
            and due_date < today
        )

        # Future/not-yet-due assessments must not
        # reduce submission compliance.
        if not is_due:

            future_trackers += 1

            continue

        due_trackers += 1

        expected = int(
            tracker.expected_student_count
            or 0
        )

        submitted = int(
            tracker.submitted_result_count
            or 0
        )

        non_participation = int(
            tracker.non_participation_count
            or 0
        )

        missing = int(
            tracker.missing_result_count
            or 0
        )

        resolved = (
            submitted
            + non_participation
        )

        expected_students_due += (
            expected
        )

        resolved_students_due += (
            resolved
        )

        missing_students_due += (
            missing
        )

        # ---------------------------------------------
        # Complete / outstanding
        # ---------------------------------------------

        if status == "Results Complete":

            complete_due_trackers += 1

            continue

        outstanding_due_trackers += 1
        overdue_trackers += 1

        responsible_key = (
            tracker.responsible_user
            or tracker.instructor
        )

        if responsible_key:

            responsible_people.add(
                responsible_key
            )

        attention_items.append({
            **tracker,

            "attention_reason":
                "Assessment Results Overdue",

            "overdue":
                True,
        })

    # =====================================================
    # Compliance
    # =====================================================

    submission_rate = (
        _percentage(
            complete_due_trackers,
            due_trackers,
        )
    )

    student_completion_rate = (
        _percentage(
            resolved_students_due,
            expected_students_due,
        )
    )

    status = (
        _target_status(
            submission_rate,
            target,
        )
    )

    return {
        "target":
            target,

        "status":
            status,

        # Plan-level management compliance
        "submission_rate":
            submission_rate,

        # Student-level result coverage
        "student_completion_rate":
            student_completion_rate,

        "total_trackers":
            total_trackers,

        "due_trackers":
            due_trackers,

        "complete_due_trackers":
            complete_due_trackers,

        "outstanding_due_trackers":
            outstanding_due_trackers,

        "overdue_trackers":
            overdue_trackers,

        "future_or_not_due_trackers":
            future_trackers,

        "cancelled_trackers":
            cancelled_trackers,

        "awaiting_plan_submission":
            awaiting_plan_submission,

        "instructor_mapping_errors":
            instructor_mapping_errors,

        "teachers_outstanding":
            len(
                responsible_people
            ),

        "expected_students_due":
            expected_students_due,

        "resolved_students_due":
            resolved_students_due,

        "missing_students_due":
            missing_students_due,

        "attention_items":
            attention_items[:50],
    }


# =========================================================
# Academic Performance
# =========================================================

def get_performance_summary(
    school_term,
):
    """
    Aggregate generated Student Performance Summary
    records.

    Important:
    overall_percentage, position and rank_out_of are
    treated as authoritative calculated values.

    This function does NOT recalculate ranking.
    """

    periods = frappe.get_all(
        "School Performance Period",

        filters={
            "school_term":
                school_term,
        },

        fields=[
            "name",
            "period_name",
            "academic_year",
            "school_term",
            "main_student_group",

            "result_status_filter",
            "missing_result_policy",
            "tie_method",

            "minimum_subjects",
            "rounding_precision",
        ],

        order_by=(
            "main_student_group asc, "
            "creation asc"
        ),
    )

    if not periods:

        return {
            "available":
                False,

            "status":
                "no_data",

            "period_count":
                0,

            "students_analysed":
                0,

            "complete_students":
                0,

            "incomplete_students":
                0,

            "school_average":
                None,

            "duplicate_students":
                0,

            "duplicate_group_periods":
                [],

            "groups":
                [],
        }

    period_names = [
        period.name
        for period in periods
    ]

    summaries = frappe.get_all(
        "Student Performance Summary",

        filters={
            "performance_period": [
                "in",
                period_names,
            ],

            "docstatus": [
                "<",
                2,
            ],
        },

        fields=[
            "name",

            "performance_period",

            "student",
            "student_name",

            "academic_year",
            "school_term",
            "main_student_group",

            "status",

            "total_subjects",

            "overall_percentage",

            "position",
            "rank_out_of",

            "docstatus",
            "modified",
        ],

        order_by=(
            "main_student_group asc, "
            "position asc, "
            "overall_percentage desc"
        ),
    )

    # =====================================================
    # Detect ambiguous configurations
    # =====================================================

    periods_by_group = {}

    for period in periods:

        periods_by_group.setdefault(
            period.main_student_group,
            []
        ).append(
            period.name
        )

    duplicate_group_periods = [
        {
            "student_group":
                student_group,

            "performance_periods":
                names,
        }

        for student_group, names
        in periods_by_group.items()

        if len(names) > 1
    ]

    # =====================================================
    # Student duplication detection
    # =====================================================

    student_occurrences = {}

    for summary in summaries:

        if not summary.student:
            continue

        student_occurrences[
            summary.student
        ] = (
            student_occurrences.get(
                summary.student,
                0,
            )
            + 1
        )

    duplicate_students = [
        student

        for student, count
        in student_occurrences.items()

        if count > 1
    ]

    # =====================================================
    # Overall counts
    # =====================================================

    complete = [
        row

        for row in summaries

        if row.status == "Complete"
    ]

    incomplete = [
        row

        for row in summaries

        if row.status == "Incomplete"
    ]

    unique_students = {
        row.student

        for row in summaries

        if row.student
    }

    unique_complete_students = {
        row.student

        for row in complete

        if row.student
    }

    unique_incomplete_students = {
        row.student

        for row in incomplete

        if row.student
    }

    # =====================================================
    # School Average
    #
    # Avoid silently double-counting students if multiple
    # performance periods exist for the same student.
    # =====================================================

    school_average = None

    if (
        complete
        and not duplicate_students
    ):

        percentages = [
            float(
                row.overall_percentage
                or 0
            )

            for row in complete
        ]

        school_average = round(
            sum(
                percentages
            )
            / len(
                percentages
            ),
            1,
        )

    # =====================================================
    # Group / Period Summary
    # =====================================================

    summaries_by_period = {}

    for row in summaries:

        summaries_by_period.setdefault(
            row.performance_period,
            []
        ).append(
            row
        )

    group_results = []

    for period in periods:

        period_rows = (
            summaries_by_period.get(
                period.name,
                [],
            )
        )

        period_complete = [
            row

            for row in period_rows

            if row.status == "Complete"
        ]

        period_incomplete = [
            row

            for row in period_rows

            if row.status == "Incomplete"
        ]

        percentages = [
            float(
                row.overall_percentage
                or 0
            )

            for row in period_complete
        ]

        average = (
            round(
                sum(percentages)
                / len(percentages),
                1,
            )
            if percentages
            else None
        )

        highest = (
            round(
                max(percentages),
                1,
            )
            if percentages
            else None
        )

        lowest = (
            round(
                min(percentages),
                1,
            )
            if percentages
            else None
        )

        group_results.append({
            "performance_period":
                period.name,

            "period_name":
                period.period_name
                or period.name,

            "student_group":
                period.main_student_group,

            "result_status_filter":
                period.result_status_filter,

            "missing_result_policy":
                period.missing_result_policy,

            "tie_method":
                period.tie_method,

            "minimum_subjects":
                period.minimum_subjects,

            "students":
                len(
                    period_rows
                ),

            "complete_students":
                len(
                    period_complete
                ),

            "incomplete_students":
                len(
                    period_incomplete
                ),

            "average":
                average,

            "highest":
                highest,

            "lowest":
                lowest,
        })

    # =====================================================
    # Status
    # =====================================================

    if (
        duplicate_students
        or duplicate_group_periods
    ):

        status = "data_issue"

    elif not complete:

        status = "no_data"

    elif incomplete:

        status = "incomplete"

    else:

        status = "ready"

    return {
        "available":
            True,

        "status":
            status,

        "period_count":
            len(
                periods
            ),

        "students_analysed":
            len(
                unique_students
            ),

        "complete_students":
            len(
                unique_complete_students
            ),

        "incomplete_students":
            len(
                unique_incomplete_students
            ),

        "school_average":
            school_average,

        "duplicate_students":
            len(
                duplicate_students
            ),

        "duplicate_student_ids":
            duplicate_students[:20],

        "duplicate_group_periods":
            duplicate_group_periods,

        "groups":
            group_results,
    }


# =========================================================
# Academic MIS
# =========================================================

def get_academic_mis(
    school_term,
    settings,
):
    """
    Return academic operations and outcome information
    for the Executive MIS.
    """

    cycles = get_examination_cycles(
        school_term
    )

    preparation = (
        get_exam_preparation_summary(
            school_term=school_term,
            cycles=cycles,
            settings=settings,
        )
    )

    result_submission = (
        get_result_submission_summary(
            school_term=school_term,
            settings=settings,
        )
    )

    performance = (
        get_performance_summary(
            school_term=school_term
        )
    )

    return {
        "cycles": [
            {
                "name":
                    cycle.name,

                "cycle_name":
                    (
                        cycle.cycle_name
                        or cycle.name
                    ),

                "assessment_type":
                    cycle.assessment_type,

                "assessment_group":
                    cycle.assessment_group,

                "status":
                    cycle.status,

                "exam_start_date":
                    (
                        str(
                            cycle.exam_start_date
                        )
                        if cycle.exam_start_date
                        else None
                    ),

                "exam_end_date":
                    (
                        str(
                            cycle.exam_end_date
                        )
                        if cycle.exam_end_date
                        else None
                    ),
            }

            for cycle in cycles
        ],

        "cycle_count":
            len(
                cycles
            ),

        "preparation":
            preparation,

        "result_submission":
            result_submission,

        "performance":
            performance,
    }