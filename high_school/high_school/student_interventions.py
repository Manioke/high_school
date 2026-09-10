from statistics import mean, pstdev

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now_datetime, nowdate

from high_school.high_school.mis.settings import get_mis_settings
from high_school.high_school.mis.persistent_absence import get_student_absence_analysis


CLOSED_STATUSES = ("Closed - Successful", "Closed - Not Required")
OPEN_STATUSES = ("Diagnosis Required", "Action Planned", "In Progress", "Ready for Review", "Overdue", "Escalated")
MANAGER_ROLES = {"System Manager", "Education Manager", "Academics User"}


def _enabled_user(user):
    return user if user and frappe.db.get_value("User", user, "enabled") else None


def _fallback_owner(settings):
    for user in (
        settings.get("default_intervention_owner"),
        settings.get("school_counselor_user"),
        frappe.session.user if frappe.session.user != "Guest" else None,
        "Administrator",
    ):
        if _enabled_user(user):
            return user
    return "Administrator"


def _academic_responsibility(school_term, student_group, course, settings):
    rows = frappe.get_all(
        "Assessment Result Submission Tracker",
        filters={"school_term": school_term, "student_group": student_group, "course": course},
        fields=["responsible_user", "hod_user"],
        order_by="modified desc",
        limit_page_length=1,
    )
    row = rows[0] if rows else {}
    hod = _enabled_user(row.get("hod_user"))
    owner = hod or _enabled_user(row.get("responsible_user")) or _fallback_owner(settings)
    return owner, hod


def _notify(user, subject, plan):
    if not _enabled_user(user):
        return
    notification = frappe.new_doc("Notification Log")
    notification.for_user = user
    notification.from_user = frappe.session.user
    notification.subject = subject
    notification.type = "Alert"
    notification.document_type = "Student Intervention Plan"
    notification.document_name = plan.name
    notification.insert(ignore_permissions=True)


def assign_plan_todo(user, plan, description, due_date=None):
    if not _enabled_user(user):
        return None
    filters = {
        "allocated_to": user,
        "reference_type": "Student Intervention Plan",
        "reference_name": plan.name,
        "description": description,
        "status": "Open",
    }
    existing = frappe.db.get_value("ToDo", filters)
    if existing:
        return existing
    todo = frappe.new_doc("ToDo")
    todo.update({
        **filters,
        "date": due_date or plan.review_date,
        "assigned_by": frappe.session.user,
    })
    todo.insert(ignore_permissions=True)
    return todo.name


def _open_plan(student, school_term, intervention_type, course=None, attendance_scope=None):
    filters = {
        "student": student,
        "school_term": school_term,
        "intervention_type": intervention_type,
        "status": ["in", OPEN_STATUSES],
    }
    if intervention_type == "Academic":
        filters["course"] = course
    elif intervention_type == "Attendance":
        filters["attendance_scope"] = attendance_scope
    return frappe.db.get_value("Student Intervention Plan", filters)


def _closed_plan(student, school_term, intervention_type, course=None, attendance_scope=None, source_document=None):
    filters = {
        "student": student,
        "school_term": school_term,
        "intervention_type": intervention_type,
        "status": ["in", CLOSED_STATUSES],
    }
    if intervention_type == "Academic":
        filters["course"] = course
        if source_document:
            filters["source_document"] = source_document
    else:
        filters["attendance_scope"] = attendance_scope
    rows = frappe.get_all(
        "Student Intervention Plan",
        filters=filters,
        fields=["name", "resolved_evidence_count"],
        order_by="modified desc",
        limit_page_length=1,
    )
    return rows[0] if rows else None


def _create_or_update_plan(values):
    existing = _open_plan(
        values["student"],
        values["school_term"],
        values["intervention_type"],
        values.get("course"),
        values.get("attendance_scope"),
    )
    created = False
    if existing:
        plan = frappe.get_doc("Student Intervention Plan", existing)
        for fieldname in (
            "source_doctype", "source_document", "trigger_reason", "baseline_metric",
            "baseline_value", "trigger_threshold", "class_average", "evidence_count",
            "student_group", "hod_user",
        ):
            if fieldname in values:
                plan.set(fieldname, values.get(fieldname))
        plan.save(ignore_permissions=True)
    else:
        plan = frappe.new_doc("Student Intervention Plan")
        plan.update(values)
        plan.insert(ignore_permissions=True)
        created = True
        _notify(plan.assigned_to, _("New student intervention requires diagnosis"), plan)
        assign_plan_todo(
            plan.assigned_to,
            plan,
            _("Diagnose and manage this student intervention"),
            plan.review_date,
        )
        if plan.hod_user and plan.hod_user != plan.assigned_to:
            _notify(plan.hod_user, _("New student intervention requires HOD review"), plan)
    return plan, created


def _course_statistics(summary, course):
    rows = frappe.db.sql(
        """
        SELECT result.percentage
        FROM `tabSchool Performance Course Result` result
        INNER JOIN `tabStudent Performance Summary` summary ON summary.name = result.parent
        WHERE summary.performance_period = %(performance_period)s
          AND summary.docstatus = 1
          AND result.course = %(course)s
          AND result.status = 'Complete'
          AND result.percentage IS NOT NULL
        """,
        {"performance_period": summary.performance_period, "course": course},
        as_dict=True,
    )
    scores = [flt(row.percentage) for row in rows]
    return {
        "count": len(scores),
        "average": round(mean(scores), 1) if scores else None,
        "standard_deviation": pstdev(scores) if len(scores) >= 2 else 0,
        "scores": scores,
    }


def evaluate_academic_trigger(score, peer_scores, absolute_threshold=50, deviation_threshold=1.5):
    scores = [flt(value) for value in peer_scores]
    score = flt(score)
    raw_average = mean(scores) if scores else None
    average = round(raw_average, 1) if raw_average is not None else None
    deviation = pstdev(scores) if len(scores) >= 2 else 0
    statistical_limit = None
    if len(scores) >= 5 and deviation > 0:
        statistical_limit = raw_average - flt(deviation_threshold) * deviation
    return {
        "triggered": score < flt(absolute_threshold) or (
            statistical_limit is not None and score < statistical_limit
        ),
        "absolute_trigger": score < flt(absolute_threshold),
        "statistical_trigger": statistical_limit is not None and score < statistical_limit,
        "average": average,
        "standard_deviation": deviation,
        "statistical_limit": statistical_limit,
        "count": len(scores),
    }


def sync_academic_interventions_from_summary(doc, method=None):
    if int(doc.docstatus or 0) != 1:
        return []
    settings = get_mis_settings()
    if not settings.get("auto_create_academic_interventions"):
        return []

    absolute_threshold = flt(settings.get("academic_intervention_threshold") or 50)
    deviation_threshold = flt(settings.get("academic_intervention_standard_deviations") or 1.5)
    owner_cache = {}
    results = []
    for row in doc.course_results or []:
        if row.status != "Complete" or row.percentage is None:
            continue
        score = flt(row.percentage)
        course_stats = _course_statistics(doc, row.course)
        stats = evaluate_academic_trigger(
            score,
            course_stats["scores"],
            absolute_threshold,
            deviation_threshold,
        )
        if not stats["triggered"]:
            continue

        if _closed_plan(
            doc.student, doc.school_term, "Academic", course=row.course, source_document=doc.name
        ):
            continue

        reasons = []
        if stats["absolute_trigger"]:
            reasons.append("Score {0:.1f}% is below the {1:.1f}% school threshold".format(score, absolute_threshold))
        if stats["statistical_trigger"]:
            reasons.append("Score is more than {0:g} standard deviations below the course-group mean".format(deviation_threshold))

        cache_key = (doc.main_student_group, row.course)
        if cache_key not in owner_cache:
            owner_cache[cache_key] = _academic_responsibility(
                doc.school_term, doc.main_student_group, row.course, settings
            )
        owner, hod = owner_cache[cache_key]
        correlated_attendance_plan = _open_plan(
            doc.student, doc.school_term, "Attendance", attendance_scope="Daily"
        ) or _open_plan(
            doc.student, doc.school_term, "Attendance", attendance_scope="Course"
        )
        suggested_actions = []
        counselor = _enabled_user(settings.get("school_counselor_user"))
        if correlated_attendance_plan:
            reasons.append("The student also has an active persistent-attendance intervention")
            if counselor:
                suggested_actions.append({
                    "action_type": "Counselor Referral",
                    "description": "Review whether attendance, wellbeing, or home circumstances are contributing to the academic result and report findings to the HOD.",
                    "assigned_to": counselor,
                    "due_date": add_days(nowdate(), 7),
                    "status": "Not Started",
                })
        plan, created = _create_or_update_plan({
            "student": doc.student,
            "intervention_type": "Academic",
            "school_term": doc.school_term,
            "course": row.course,
            "student_group": doc.main_student_group,
            "source_doctype": doc.doctype,
            "source_document": doc.name,
            "trigger_reason": "; ".join(reasons),
            "baseline_metric": "Assessment Score",
            "baseline_value": score,
            "trigger_threshold": absolute_threshold,
            "class_average": course_stats["average"],
            "evidence_count": course_stats["count"],
            "metric_direction": "Higher is Better",
            "status": "Diagnosis Required",
            "priority": "High" if score < absolute_threshold - 10 else "Medium",
            "assigned_to": owner,
            "hod_user": hod,
            "opened_on": now_datetime(),
            "review_date": add_days(nowdate(), max(1, int(settings.get("intervention_follow_up_days") or 21))),
            "follow_up_metric": "Re-assessment Score",
            "actions": suggested_actions,
        })
        results.append({"name": plan.name, "created": created})
    return results


def _school_term_for_date(attendance_date):
    rows = frappe.get_all(
        "School Term",
        filters={"start_date": ["<=", attendance_date], "end_date": [">=", attendance_date]},
        fields=["name", "start_date", "end_date"],
        order_by="start_date desc",
        limit_page_length=1,
    )
    return rows[0] if rows else None


def sync_attendance_intervention(student, attendance_date, attendance_type, source_document=None):
    settings = get_mis_settings()
    if not settings.get("auto_create_attendance_interventions"):
        return None
    term = _school_term_for_date(attendance_date)
    if not term:
        return None
    analysis = get_student_absence_analysis(
        term.start_date, term.end_date, attendance_type, settings
    )
    row = next((item for item in analysis.get("flagged_students") or [] if item.get("student") == student), None)
    if not row:
        return None
    closed = _closed_plan(
        student, term.name, "Attendance", attendance_scope=attendance_type.title()
    )
    if closed and int(closed.resolved_evidence_count or 0) >= int(row.get("counted_records") or 0):
        return {"name": closed.name, "created": False, "managed": True}
    attendance_rate = round(100 - flt(row.get("absence_rate")), 1)
    owner = _fallback_owner(settings)
    plan, created = _create_or_update_plan({
        "student": student,
        "intervention_type": "Attendance",
        "attendance_scope": attendance_type.title(),
        "school_term": term.name,
        "source_doctype": "Student Attendance",
        "source_document": source_document,
        "trigger_reason": "Absence rate {0:.1f}% meets or exceeds the {1:.1f}% persistent-absence threshold".format(
            flt(row.get("absence_rate")), flt(row.get("threshold"))
        ),
        "baseline_metric": "Attendance Rate",
        "baseline_value": attendance_rate,
        "trigger_threshold": round(100 - flt(row.get("threshold")), 1),
        "evidence_count": int(row.get("counted_records") or 0),
        "metric_direction": "Higher is Better",
        "status": "Diagnosis Required",
        "priority": "High",
        "assigned_to": owner,
        "opened_on": now_datetime(),
        "review_date": add_days(nowdate(), max(1, int(settings.get("intervention_follow_up_days") or 21))),
        "follow_up_metric": "Attendance Rate at Review",
    })
    return {"name": plan.name, "created": created}


def get_or_create_attendance_plan(student, school_term, attendance_type, absence_rate, evidence_count):
    settings = get_mis_settings()
    scope = (attendance_type or "").strip().title()
    if scope not in {"Daily", "Course"}:
        frappe.throw(_("Attendance Type must be Daily or Course."))
    closed = _closed_plan(student, school_term, "Attendance", attendance_scope=scope)
    if closed and int(closed.resolved_evidence_count or 0) >= int(evidence_count or 0):
        return {"name": closed.name, "created": False, "managed": True}
    owner = _fallback_owner(settings)
    plan, created = _create_or_update_plan({
        "student": student,
        "intervention_type": "Attendance",
        "attendance_scope": scope,
        "school_term": school_term,
        "trigger_reason": "Absence rate {0:.1f}% meets or exceeds the persistent-absence threshold".format(flt(absence_rate)),
        "baseline_metric": "Attendance Rate",
        "baseline_value": round(100 - flt(absence_rate), 1),
        "trigger_threshold": round(100 - flt(settings.get("persistent_absence_threshold")), 1),
        "evidence_count": int(evidence_count or 0),
        "metric_direction": "Higher is Better",
        "status": "Diagnosis Required",
        "priority": "High",
        "assigned_to": owner,
        "opened_on": now_datetime(),
        "review_date": add_days(nowdate(), max(1, int(settings.get("intervention_follow_up_days") or 21))),
        "follow_up_metric": "Attendance Rate at Review",
    })
    return {"name": plan.name, "created": created}


def queue_attendance_intervention_refresh(doc, method=None):
    if not doc.student or not doc.date:
        return
    attendance_type = "course" if doc.get("course_schedule") else "daily"
    frappe.enqueue(
        "high_school.high_school.student_interventions.sync_attendance_intervention",
        student=doc.student,
        attendance_date=str(doc.date),
        attendance_type=attendance_type,
        source_document=doc.name,
        enqueue_after_commit=True,
    )


@frappe.whitelist()
def refresh_intervention_plans(school_term):
    frappe.only_for(("Academics User", "Education Manager", "System Manager"))
    academic = []
    for name in frappe.get_all(
        "Student Performance Summary",
        filters={"school_term": school_term, "docstatus": 1},
        pluck="name",
        limit_page_length=0,
    ):
        academic.extend(sync_academic_interventions_from_summary(frappe.get_doc("Student Performance Summary", name)))

    term = frappe.get_doc("School Term", school_term)
    settings = get_mis_settings()
    attendance = []
    if settings.get("auto_create_attendance_interventions"):
        for mode in ("daily", "course"):
            enabled = settings.get("track_daily_attendance") if mode == "daily" else settings.get("track_course_attendance")
            if not enabled:
                continue
            analysis = get_student_absence_analysis(term.start_date, term.end_date, mode, settings)
            for row in analysis.get("flagged_students") or []:
                result = sync_attendance_intervention(row["student"], term.end_date, mode)
                if result:
                    attendance.append(result)
    refresh_overdue_intervention_plans()
    return {"academic": academic, "attendance": attendance}


def refresh_overdue_intervention_plans():
    settings = get_mis_settings()
    principal = _enabled_user(settings.get("school_principal_user"))
    rows = frappe.get_all(
        "Student Intervention Plan",
        filters={"status": ["in", ("Diagnosis Required", "Action Planned", "In Progress", "Ready for Review")], "review_date": ["<", nowdate()]},
        fields=["name", "assigned_to"],
        limit_page_length=0,
    )
    for row in rows:
        plan = frappe.get_doc("Student Intervention Plan", row.name)
        plan.status = "Overdue"
        if principal:
            plan.escalated_to = principal
            plan.escalated_on = now_datetime()
        plan.save(ignore_permissions=True)
        _notify(principal or plan.assigned_to, _("Overdue student intervention requires review"), plan)
        assign_plan_todo(
            principal or plan.assigned_to,
            plan,
            _("Review overdue student intervention"),
            nowdate(),
        )
    return len(rows)


def refresh_current_intervention_plans():
    """Daily safety net for bulk imports and scores submitted before peers."""
    terms = frappe.get_all(
        "School Term",
        filters={"start_date": ["<=", nowdate()], "end_date": [">=", nowdate()]},
        pluck="name",
        limit_page_length=0,
    )
    for school_term in terms:
        refresh_intervention_plans(school_term)


def get_intervention_summary(school_term):
    rows = frappe.get_all(
        "Student Intervention Plan",
        filters={"school_term": school_term},
        fields=["name", "student", "student_name", "intervention_type", "course", "status", "priority", "assigned_to", "review_date", "baseline_value", "follow_up_value", "outcome"],
        order_by="review_date asc, priority desc",
        limit_page_length=0,
    )
    open_rows = [row for row in rows if row.status not in CLOSED_STATUSES]
    overdue = [row for row in open_rows if row.status in {"Overdue", "Escalated"} or (row.review_date and getdate(row.review_date) < getdate(nowdate()))]
    closed_success = [row for row in rows if row.status == "Closed - Successful"]
    academic_improvements = [
        flt(row.follow_up_value) - flt(row.baseline_value)
        for row in closed_success
        if row.intervention_type == "Academic" and row.follow_up_value is not None
    ]
    return {
        "total": len(rows),
        "open": len(open_rows),
        "overdue": len(overdue),
        "closed_successful": len(closed_success),
        "academic_open": sum(row.intervention_type == "Academic" for row in open_rows),
        "attendance_open": sum(row.intervention_type == "Attendance" for row in open_rows),
        "average_academic_improvement": (
            round(mean(academic_improvements), 1) if academic_improvements else None
        ),
        "items": open_rows[:50],
    }


def intervention_permission_query(user=None):
    user = user or frappe.session.user
    if set(frappe.get_roles(user)) & MANAGER_ROLES:
        return ""
    escaped = frappe.db.escape(user)
    return "(`tabStudent Intervention Plan`.`assigned_to` = {0} OR `tabStudent Intervention Plan`.`hod_user` = {0} OR EXISTS (SELECT 1 FROM `tabStudent Intervention Action` action WHERE action.parent = `tabStudent Intervention Plan`.name AND action.parenttype = 'Student Intervention Plan' AND action.assigned_to = {0}))".format(escaped)


def has_intervention_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if set(frappe.get_roles(user)) & MANAGER_ROLES:
        return True
    if user in {doc.assigned_to, doc.hod_user}:
        return True
    return any(row.assigned_to == user for row in doc.actions or [])
