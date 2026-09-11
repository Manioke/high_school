from statistics import mean, pstdev

import frappe
from frappe import _
from frappe.utils import escape_html, flt, now_datetime, nowdate

from high_school.high_school.mis.settings import get_mis_settings


CLOSED_STATUSES = ("Closed - Successful", "Closed - Not Required")
OPEN_STATUSES = (
    "Diagnosis Required", "Action Planned", "In Progress", "Monitoring",
    "Ready for Review", "Overdue", "Escalated",
)
MONITORED_STATUSES = {"Action Planned", "In Progress", "Monitoring", "Ready for Review"}
MANAGER_ROLES = {"System Manager", "Education Manager", "Academics User"}


def _enabled_user(user):
    return user if user and frappe.db.get_value("User", user, "enabled") else None


def _instructor_user(instructor):
    if not instructor:
        return None
    fields = {field.fieldname for field in frappe.get_meta("Instructor").fields}
    for fieldname in ("user", "user_id"):
        if fieldname in fields:
            user = frappe.db.get_value("Instructor", instructor, fieldname)
            if _enabled_user(user):
                return user
    if "employee" in fields:
        employee = frappe.db.get_value("Instructor", instructor, "employee")
        user = frappe.db.get_value("Employee", employee, "user_id") if employee else None
        if _enabled_user(user):
            return user
    return None


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


def _role_users(roles):
    users = frappe.get_all(
        "Has Role", filters={"role": ["in", list(roles)]},
        pluck="parent", limit_page_length=0,
    )
    return sorted({user for user in users if _enabled_user(user)})


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


def _email_users(users, subject, message, settings):
    if not settings.get("send_intervention_email_notifications"):
        return []
    emails = []
    for user in sorted(set(users) - {None, "", "Guest"}):
        email = frappe.db.get_value("User", {"name": user, "enabled": 1}, "email")
        if email:
            emails.append(email)
    if emails:
        frappe.sendmail(recipients=emails, subject=subject, message=message, now=False)
    return emails


def _action_summary(plan):
    if not plan.actions:
        return _("No action items have been recorded yet.")
    return "<ul>{0}</ul>".format(
        "".join(
            "<li><b>{0}</b>: {1} — {2} ({3})</li>".format(
                escape_html(row.action_type or "Action"),
                escape_html(row.description or ""),
                escape_html(row.assigned_to or "Unassigned"),
                escape_html(row.status or "Not Started"),
            )
            for row in plan.actions
        )
    )


def _plan_message(plan, heading, detail):
    return """
        <p>{heading}</p>
        <p><b>Student:</b> {student}<br>
        <b>Course:</b> {course}<br>
        <b>Student Group:</b> {group}<br>
        <b>School Term:</b> {term}<br>
        <b>Reason:</b> {reason}</p>
        <p>{detail}</p>
        <p><b>Recorded action plan</b></p>{actions}
        <p><a href="{url}">Open Student Intervention Plan {name}</a></p>
    """.format(
        heading=escape_html(heading),
        student=escape_html(plan.student_name or plan.student),
        course=escape_html(plan.course or ""),
        group=escape_html(plan.student_group or ""),
        term=escape_html(plan.school_term or ""),
        reason=escape_html(plan.trigger_reason or ""),
        detail=escape_html(detail),
        actions=_action_summary(plan),
        url=escape_html(frappe.utils.get_url_to_form(plan.doctype, plan.name)),
        name=escape_html(plan.name),
    )


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
    todo.update({**filters, "date": due_date or nowdate(), "assigned_by": frappe.session.user})
    todo.insert(ignore_permissions=True)
    return todo.name


def _open_plan(student, school_term, intervention_type, course=None, student_group=None):
    filters = {
        "student": student, "school_term": school_term,
        "intervention_type": intervention_type, "status": ["in", OPEN_STATUSES],
    }
    if course:
        filters["course"] = course
    if student_group:
        filters["student_group"] = student_group
    return frappe.db.get_value("Student Intervention Plan", filters)


def _closed_plan(student, school_term, intervention_type, course=None, source_document=None):
    filters = {
        "student": student, "school_term": school_term,
        "intervention_type": intervention_type, "status": ["in", CLOSED_STATUSES],
    }
    if course:
        filters["course"] = course
    if source_document:
        filters["source_document"] = source_document
    return frappe.db.get_value("Student Intervention Plan", filters)


def _create_or_update_plan(values, settings):
    existing = _open_plan(
        values["student"], values["school_term"], values["intervention_type"],
        values.get("course"), values.get("student_group"),
    )
    created = False
    if existing:
        plan = frappe.get_doc("Student Intervention Plan", existing)
        previous_owner = plan.assigned_to
        for fieldname in (
            "source_doctype", "source_document", "trigger_reason", "baseline_metric",
            "baseline_value", "baseline_overall_percentage", "initial_consecutive_absences",
            "trigger_threshold", "class_average", "evidence_count", "student_group",
            "instructor", "assigned_to", "hod_user", "consecutive_low_periods",
        ):
            if fieldname in values:
                plan.set(fieldname, values.get(fieldname))
        plan.save(ignore_permissions=True)
        if plan.assigned_to and plan.assigned_to != previous_owner:
            _notify(plan.assigned_to, _("Student intervention reassigned to you"), plan)
            assign_plan_todo(
                plan.assigned_to, plan, _("Diagnose and plan this student intervention")
            )
            _email_users(
                [plan.assigned_to],
                _("Student intervention assigned: {0} / {1}").format(
                    plan.student_name or plan.student, plan.course
                ),
                _plan_message(
                    plan,
                    _("This student intervention has been reassigned to you."),
                    _("Open the plan, record the diagnosis, add concrete actions, and begin monitoring."),
                ),
                settings,
            )
    else:
        plan = frappe.new_doc("Student Intervention Plan")
        plan.update(values)
        plan.insert(ignore_permissions=True)
        created = True
        _notify(plan.assigned_to, _("New student intervention requires an action plan"), plan)
        assign_plan_todo(plan.assigned_to, plan, _("Diagnose and plan this student intervention"))
        _email_users(
            [plan.assigned_to],
            _("Student intervention assigned: {0} / {1}").format(
                plan.student_name or plan.student, plan.course
            ),
            _plan_message(
                plan, _("A student intervention has been assigned to you."),
                _("Open the plan, record the diagnosis, add concrete actions, and begin monitoring."),
            ),
            settings,
        )
    return plan, created


def _escalation_users(settings):
    users = {
        _enabled_user(settings.get("school_counselor_user")),
        _enabled_user(settings.get("school_principal_user")),
    }
    users.update(_role_users({"Education Manager", "Academics User"}))
    return sorted(users - {None, ""})


def escalate_plan(plan, reason, settings):
    recipients = _escalation_users(settings)
    already_escalated = plan.status == "Escalated" and plan.escalation_reason == reason
    plan.status = "Escalated"
    plan.outcome = "No Improvement - Escalated"
    plan.escalation_reason = reason
    plan.escalation_recipients = ", ".join(recipients)
    plan.escalated_to = (
        _enabled_user(settings.get("school_counselor_user"))
        or _enabled_user(settings.get("school_principal_user"))
        or (recipients[0] if recipients else plan.assigned_to)
    )
    plan.escalated_on = plan.escalated_on or now_datetime()
    plan.save(ignore_permissions=True)
    if already_escalated:
        return plan
    for user in recipients:
        _notify(user, _("Student intervention automatically escalated"), plan)
        assign_plan_todo(user, plan, _("Review escalated student intervention"))
    _email_users(
        recipients,
        _("Escalated student intervention: {0} / {1}").format(
            plan.student_name or plan.student, plan.course
        ),
        _plan_message(plan, _("This intervention was escalated automatically."), reason),
        settings,
    )
    return plan


@frappe.whitelist()
def escalate_intervention_plan(plan_name, reason):
    plan = frappe.get_doc("Student Intervention Plan", plan_name)
    plan.check_permission("write")
    reason = (reason or "").strip()
    if not reason:
        frappe.throw(_("Enter the reason this intervention requires management escalation."))
    return escalate_plan(plan, reason, get_mis_settings()).name


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
        {"performance_period": summary.performance_period, "course": course}, as_dict=True,
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
        "average": average, "standard_deviation": deviation,
        "statistical_limit": statistical_limit, "count": len(scores),
    }


def _student_schedule_groups(student, academic_year, course):
    group_columns = set(frappe.db.get_table_columns("Student Group Student") or [])
    filters = {"student": student}
    if "active" in group_columns:
        filters["active"] = 1
    groups = frappe.get_all(
        "Student Group Student", filters=filters, pluck="parent", limit_page_length=0
    )
    if not groups:
        return []
    schedule_fields = {field.fieldname for field in frappe.get_meta("Course Schedule").fields}
    schedule_filters = {
        "student_group": ["in", groups], "course": course, "docstatus": ["<", 2],
    }
    if "academic_year" in schedule_fields:
        schedule_filters["academic_year"] = academic_year
    return frappe.get_all(
        "Course Schedule", filters=schedule_filters,
        fields=["student_group", "instructor"], limit_page_length=0,
    )


def _academic_responsibility(summary, course, settings):
    component_plans = sorted({
        row.assessment_plan for row in (summary.component_results or [])
        if row.course == course and row.assessment_plan
    })
    trackers = frappe.get_all(
        "Assessment Result Submission Tracker",
        filters={"assessment_plan": ["in", component_plans]},
        fields=["responsible_user", "instructor", "hod_user", "student_group"],
        limit_page_length=0,
    ) if component_plans else []
    responsible_users = sorted({
        user for row in trackers if (user := _enabled_user(row.responsible_user))
    })
    instructors = sorted({row.instructor for row in trackers if row.instructor})
    groups = sorted({row.student_group for row in trackers if row.student_group})
    hod_users = sorted({
        user for row in trackers if (user := _enabled_user(row.hod_user))
    })
    if not responsible_users:
        schedule_rows = _student_schedule_groups(summary.student, summary.academic_year, course)
        instructors = sorted({row.instructor for row in schedule_rows if row.instructor})
        groups = sorted({row.student_group for row in schedule_rows if row.student_group})
        responsible_users = sorted({
            user for instructor in instructors if (user := _instructor_user(instructor))
        })
    issue = None
    if len(responsible_users) != 1:
        issue = (
            _("No enabled User could be resolved for the scheduled course instructor.")
            if not responsible_users
            else _("More than one responsible instructor User was resolved for this student and course.")
        )
    return {
        "owner": responsible_users[0] if len(responsible_users) == 1 else _fallback_owner(settings),
        "instructor": instructors[0] if len(instructors) == 1 else None,
        "student_group": groups[0] if len(groups) == 1 else summary.main_student_group,
        "hod_user": hod_users[0] if len(hod_users) == 1 else None,
        "issue": issue,
    }


def _previous_term_summary(summary):
    current_term = frappe.db.get_value(
        "School Term", summary.school_term, ["academic_year", "start_date"], as_dict=True
    )
    if not current_term:
        return None
    previous_term = frappe.db.get_value(
        "School Term",
        {"academic_year": current_term.academic_year, "start_date": ["<", current_term.start_date]},
        "name", order_by="start_date desc",
    )
    if not previous_term:
        return None
    name = frappe.db.get_value(
        "Student Performance Summary",
        {"student": summary.student, "school_term": previous_term, "docstatus": 1, "status": "Complete"},
        "name", order_by="modified desc",
    )
    return frappe.get_doc("Student Performance Summary", name) if name else None


def _consecutive_low_terms(summary, threshold):
    current_start = frappe.db.get_value("School Term", summary.school_term, "start_date")
    if not current_start:
        return 0
    terms = frappe.get_all(
        "School Term",
        filters={"academic_year": summary.academic_year, "start_date": ["<=", current_start]},
        fields=["name", "start_date"], order_by="start_date desc", limit_page_length=0,
    )
    count = 0
    for term in terms:
        percentage = frappe.db.get_value(
            "Student Performance Summary",
            {"student": summary.student, "school_term": term.name, "docstatus": 1, "status": "Complete"},
            "overall_percentage", order_by="modified desc",
        )
        if percentage is None or flt(percentage) >= flt(threshold):
            break
        count += 1
    return count


def _evaluate_previous_academic_plans(summary, previous, settings):
    if not previous or previous.overall_percentage is None or summary.overall_percentage is None:
        return []
    change = round(flt(summary.overall_percentage) - flt(previous.overall_percentage), 1)
    names = frappe.get_all(
        "Student Intervention Plan",
        filters={
            "student": summary.student, "school_term": previous.school_term,
            "intervention_type": "Academic", "status": ["not in", CLOSED_STATUSES],
        },
        pluck="name", limit_page_length=0,
    )
    evaluated = []
    for name in names:
        plan = frappe.get_doc("Student Intervention Plan", name)
        plan.comparison_summary = summary.name
        plan.comparison_school_term = summary.school_term
        plan.comparison_overall_percentage = summary.overall_percentage
        plan.percentage_point_change = change
        plan.outcome_evaluated_on = now_datetime()
        plan.follow_up_value = summary.overall_percentage
        plan.follow_up_evidence = summary.name
        if change > 0:
            plan.status = "Closed - Successful"
            plan.outcome = "Improved - Continue Monitoring"
            plan.resolution_notes = _(
                "Automatically closed because the next official overall result improved from {0}% to {1}% ({2:+.1f} percentage points)."
            ).format(previous.overall_percentage, summary.overall_percentage, change)
            plan.save(ignore_permissions=True)
        else:
            plan.save(ignore_permissions=True)
            escalate_plan(
                plan,
                _(
                    "The next official overall result did not improve: {0}% in {1} compared with {2}% in {3} ({4:+.1f} percentage points)."
                ).format(
                    summary.overall_percentage, summary.school_term,
                    previous.overall_percentage, previous.school_term, change,
                ), settings,
            )
        evaluated.append(plan.name)
    return evaluated


def _weak_component_text(summary, course, threshold):
    rows = [
        row for row in (summary.component_results or [])
        if row.course == course and row.status == "Complete" and flt(row.percentage) < flt(threshold)
    ]
    if not rows:
        return ""
    return _("weak components: {0}").format(
        ", ".join("{0} {1:.1f}%".format(row.assessment_group, flt(row.percentage)) for row in rows)
    )


def sync_academic_interventions_from_summary(doc, method=None):
    if int(doc.docstatus or 0) != 1 or doc.status != "Complete":
        return []
    settings = get_mis_settings()
    if not settings.get("auto_create_academic_interventions"):
        return []
    threshold = flt(settings.get("academic_intervention_threshold") or 50)
    previous = _previous_term_summary(doc)
    evaluated = _evaluate_previous_academic_plans(doc, previous, settings)
    consecutive = _consecutive_low_terms(doc, threshold)
    if doc.overall_percentage is None or flt(doc.overall_percentage) >= threshold:
        return [{"name": name, "evaluated": True} for name in evaluated]

    deviation_threshold = flt(settings.get("academic_intervention_standard_deviations") or 1.5)
    escalation_after = max(1, int(settings.get("academic_intervention_consecutive_periods") or 2))
    results = [{"name": name, "evaluated": True} for name in evaluated]
    for row in doc.course_results or []:
        if row.status != "Complete" or row.percentage is None:
            continue
        score = flt(row.percentage)
        course_stats = _course_statistics(doc, row.course)
        stats = evaluate_academic_trigger(
            score, course_stats["scores"], threshold, deviation_threshold
        )
        if not stats["triggered"]:
            continue
        if _closed_plan(doc.student, doc.school_term, "Academic", row.course, doc.name):
            continue
        responsibility = _academic_responsibility(doc, row.course, settings)
        reasons = [
            _("Overall result {0:.1f}% is below the {1:.1f}% intervention threshold").format(
                flt(doc.overall_percentage), threshold
            )
        ]
        if stats["absolute_trigger"]:
            reasons.append(_("course result {0:.1f}% is below the threshold").format(score))
        if stats["statistical_trigger"]:
            reasons.append(
                _("course result is more than {0:g} standard deviations below its peer mean").format(
                    deviation_threshold
                )
            )
        if responsibility["issue"]:
            reasons.append(responsibility["issue"])
        component_text = _weak_component_text(doc, row.course, threshold)
        if component_text:
            reasons.append(component_text)
        plan, created = _create_or_update_plan({
            "student": doc.student, "intervention_type": "Academic",
            "school_term": doc.school_term, "course": row.course,
            "student_group": responsibility["student_group"],
            "instructor": responsibility["instructor"],
            "source_doctype": doc.doctype, "source_document": doc.name,
            "trigger_reason": "; ".join(reasons), "baseline_metric": "Course Result",
            "baseline_value": score, "baseline_overall_percentage": doc.overall_percentage,
            "trigger_threshold": threshold, "class_average": stats["average"],
            "evidence_count": stats["count"], "metric_direction": "Higher is Better",
            "status": "Diagnosis Required", "priority": "High" if score < threshold - 10 else "Medium",
            "assigned_to": responsibility["owner"], "hod_user": responsibility["hod_user"],
            "opened_on": now_datetime(), "consecutive_low_periods": consecutive,
        }, settings)
        if consecutive >= escalation_after:
            escalate_plan(
                plan,
                _(
                    "The student's overall result has remained below {0}% for {1} consecutive School Terms (configured escalation point: {2})."
                ).format(threshold, consecutive, escalation_after), settings,
            )
        results.append({"name": plan.name, "created": created})
    return results


def _school_term_for_date(attendance_date):
    rows = frappe.get_all(
        "School Term", filters={"start_date": ["<=", attendance_date], "end_date": [">=", attendance_date]},
        fields=["name", "academic_year", "start_date", "end_date"],
        order_by="start_date desc", limit_page_length=1,
    )
    return rows[0] if rows else None


def _course_attendance_rows(student, course, student_group, instructor, end_date=None, after=None):
    conditions = [
        "attendance.student = %(student)s", "attendance.docstatus = 1",
        "schedule.course = %(course)s", "schedule.student_group = %(student_group)s",
        "schedule.instructor = %(instructor)s", "schedule.docstatus < 2",
    ]
    values = {
        "student": student, "course": course,
        "student_group": student_group, "instructor": instructor,
    }
    if end_date:
        conditions.append("attendance.date <= %(end_date)s")
        values["end_date"] = end_date
    if after:
        conditions.append("attendance.creation > %(after)s")
        values["after"] = after
    return frappe.db.sql(
        """
        SELECT attendance.name, attendance.date, attendance.status, attendance.creation,
               attendance.course_schedule
        FROM `tabStudent Attendance` attendance
        INNER JOIN `tabCourse Schedule` schedule ON schedule.name = attendance.course_schedule
        WHERE {conditions}
        ORDER BY attendance.date DESC, attendance.creation DESC
        """.format(conditions=" AND ".join(conditions)), values, as_dict=True,
    )


def _leading_absence_count(rows):
    count = 0
    for row in rows:
        if row.status != "Absent":
            break
        count += 1
    return count


def _sync_course_attendance_doc(doc, settings):
    if int(doc.docstatus or 0) != 1 or not doc.course_schedule:
        return None
    schedule = frappe.db.get_value(
        "Course Schedule", doc.course_schedule,
        ["course", "student_group", "instructor"], as_dict=True,
    )
    if not schedule or not schedule.course or not schedule.student_group or not schedule.instructor:
        return None
    term = _school_term_for_date(doc.date)
    if not term:
        return None
    owner = _instructor_user(schedule.instructor)
    if not owner:
        return None
    history = _course_attendance_rows(
        doc.student, schedule.course, schedule.student_group, schedule.instructor, end_date=doc.date
    )
    consecutive = _leading_absence_count(history)
    trigger_count = max(1, int(settings.get("course_attendance_absence_trigger_count") or 3))
    plan_name = _open_plan(doc.student, term.name, "Attendance", schedule.course, schedule.student_group)
    if not plan_name and consecutive < trigger_count:
        return None
    if plan_name:
        plan = frappe.get_doc("Student Intervention Plan", plan_name)
    else:
        plan, created = _create_or_update_plan({
            "student": doc.student, "intervention_type": "Attendance",
            "attendance_scope": "Course", "school_term": term.name,
            "course": schedule.course, "student_group": schedule.student_group,
            "instructor": schedule.instructor, "source_doctype": "Student Attendance",
            "source_document": doc.name,
            "trigger_reason": _("{0} consecutive Absent records were submitted for {1} in {2}.").format(
                consecutive, schedule.course, schedule.student_group
            ),
            "baseline_metric": "Consecutive Course Absences",
            "initial_consecutive_absences": consecutive, "evidence_count": len(history),
            "metric_direction": "Lower is Better", "status": "Diagnosis Required",
            "priority": "High", "assigned_to": owner, "opened_on": now_datetime(),
        }, settings)
        return {"name": plan.name, "created": created}
    if plan.status in MONITORED_STATUSES and plan.monitoring_started_on:
        later_rows = _course_attendance_rows(
            doc.student, schedule.course, schedule.student_group,
            schedule.instructor, after=plan.monitoring_started_on,
        )
        additional_absences = sum(row.status == "Absent" for row in later_rows)
        plan.post_plan_absence_count = additional_absences
        plan.source_document = doc.name
        plan.save(ignore_permissions=True)
        escalation_count = max(1, int(settings.get("course_attendance_escalation_absence_count") or 3))
        if additional_absences >= escalation_count:
            escalate_plan(
                plan,
                _(
                    "The student recorded {0} additional absences for {1} after the instructor started the action plan (configured escalation point: {2})."
                ).format(additional_absences, schedule.course, escalation_count), settings,
            )
    return {"name": plan.name, "created": False}


def sync_attendance_intervention(student=None, attendance_date=None, attendance_type=None, source_document=None):
    settings = get_mis_settings()
    if not settings.get("auto_create_attendance_interventions") or not source_document:
        return None
    return _sync_course_attendance_doc(frappe.get_doc("Student Attendance", source_document), settings)


def get_or_create_attendance_plan(student, school_term, attendance_type=None, absence_rate=None, evidence_count=None):
    term = frappe.get_doc("School Term", school_term)
    name = frappe.db.get_value(
        "Student Attendance",
        {
            "student": student, "docstatus": 1, "status": "Absent",
            "course_schedule": ["is", "set"], "date": ["between", [term.start_date, term.end_date]],
        },
        "name", order_by="date desc, creation desc",
    )
    if not name:
        frappe.throw(_("No submitted course-attendance absence was found for this student and School Term."))
    return _sync_course_attendance_doc(
        frappe.get_doc("Student Attendance", name), get_mis_settings()
    ) or {"created": False}


def queue_attendance_intervention_refresh(doc, method=None):
    if not doc.student or not doc.date or not doc.course_schedule:
        return
    frappe.enqueue(
        "high_school.high_school.student_interventions.sync_attendance_intervention",
        student=doc.student, attendance_date=str(doc.date), attendance_type="course",
        source_document=doc.name, enqueue_after_commit=True,
    )


@frappe.whitelist()
def refresh_intervention_plans(school_term):
    frappe.only_for(("Academics User", "Education Manager", "System Manager"))
    academic = []
    for name in frappe.get_all(
        "Student Performance Summary",
        filters={"school_term": school_term, "docstatus": 1, "status": "Complete"},
        pluck="name", order_by="modified asc", limit_page_length=0,
    ):
        academic.extend(sync_academic_interventions_from_summary(frappe.get_doc("Student Performance Summary", name)))
    term = frappe.get_doc("School Term", school_term)
    settings = get_mis_settings()
    attendance = []
    for name in frappe.get_all(
        "Student Attendance",
        filters={
            "docstatus": 1, "course_schedule": ["is", "set"],
            "date": ["between", [term.start_date, term.end_date]],
        },
        pluck="name", order_by="date asc, creation asc", limit_page_length=0,
    ):
        result = _sync_course_attendance_doc(frappe.get_doc("Student Attendance", name), settings)
        if result:
            attendance.append(result)
    return {"academic": academic, "attendance": attendance}


def refresh_overdue_intervention_plans():
    """Compatibility scheduler hook: evaluate evidence, never time-based manual reviews."""
    settings = get_mis_settings()
    names = frappe.get_all(
        "Student Intervention Plan",
        filters={"intervention_type": "Attendance", "status": ["in", list(MONITORED_STATUSES)]},
        pluck="name", limit_page_length=0,
    )
    evaluated = 0
    for name in names:
        source = frappe.db.get_value("Student Intervention Plan", name, "source_document")
        if source and frappe.db.exists("Student Attendance", source):
            result = _sync_course_attendance_doc(frappe.get_doc("Student Attendance", source), settings)
            evaluated += int(bool(result))
    return evaluated


def refresh_current_intervention_plans():
    terms = frappe.get_all(
        "School Term", filters={"start_date": ["<=", nowdate()], "end_date": [">=", nowdate()]},
        pluck="name", limit_page_length=0,
    )
    for school_term in terms:
        refresh_intervention_plans(school_term)


def get_intervention_summary(school_term):
    rows = frappe.get_all(
        "Student Intervention Plan", filters={"school_term": school_term},
        fields=[
            "name", "student", "student_name", "intervention_type", "course",
            "student_group", "instructor", "status", "priority", "assigned_to",
            "monitoring_started_on", "post_plan_absence_count", "baseline_value",
            "baseline_overall_percentage", "consecutive_low_periods", "outcome",
        ],
        order_by="priority desc, modified desc", limit_page_length=0,
    )
    open_rows = [row for row in rows if row.status not in CLOSED_STATUSES]
    escalated = [row for row in open_rows if row.status in {"Overdue", "Escalated"}]
    closed_success = [row for row in rows if row.status == "Closed - Successful"]
    outcome_rows = frappe.get_all(
        "Student Intervention Plan",
        filters={"comparison_school_term": school_term, "intervention_type": "Academic"},
        fields=["student", "percentage_point_change", "outcome"], limit_page_length=0,
    )
    by_student = {}
    for row in outcome_rows:
        by_student.setdefault(row.student, row)
    outcomes = list(by_student.values())
    improved = [row for row in outcomes if flt(row.percentage_point_change) > 0]
    declined = [row for row in outcomes if flt(row.percentage_point_change) <= 0]
    return {
        "total": len(rows), "open": len(open_rows), "overdue": len(escalated),
        "closed_successful": len(closed_success),
        "academic_open": sum(row.intervention_type == "Academic" for row in open_rows),
        "attendance_open": sum(row.intervention_type == "Attendance" for row in open_rows),
        "average_academic_improvement": (
            round(mean([flt(row.percentage_point_change) for row in improved]), 1) if improved else None
        ),
        "academic_outcomes": {
            "evaluated_students": len(outcomes), "improved_students": len(improved),
            "not_improved_students": len(declined),
            "average_change": (
                round(mean([flt(row.percentage_point_change) for row in outcomes]), 1)
                if outcomes else None
            ),
        },
        "items": open_rows[:50],
    }


def intervention_permission_query(user=None):
    user = user or frappe.session.user
    if set(frappe.get_roles(user)) & MANAGER_ROLES:
        return ""
    escaped = frappe.db.escape(user)
    return "(`tabStudent Intervention Plan`.`assigned_to` = {0} OR EXISTS (SELECT 1 FROM `tabStudent Intervention Action` action WHERE action.parent = `tabStudent Intervention Plan`.name AND action.parenttype = 'Student Intervention Plan' AND action.assigned_to = {0}))".format(escaped)


def has_intervention_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if set(frappe.get_roles(user)) & MANAGER_ROLES:
        return True
    if user == doc.assigned_to:
        return True
    return any(row.assigned_to == user for row in doc.actions or [])
