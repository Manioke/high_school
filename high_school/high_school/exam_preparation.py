from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate


MANAGER_ROLES = {"System Manager", "Education Manager"}
APPROVED_STATUSES = {"Approved", "Plans Partially Created", "Complete"}


def _doctype_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _first_available(fields, *names):
	return next((name for name in names if name in fields), None)


def get_enabled_users_with_role(role):
	"""Return enabled System Users with a role, including roles from Role Profiles."""
	users = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		pluck="name",
		order_by="name asc",
	)
	return [user for user in users if role in frappe.get_roles(user)]


def _student_groups_for_batch(academic_year, student_batch):
	fields = _doctype_fields("Student Group")
	batch_field = _first_available(fields, "student_batch", "student_batch_name", "batch")
	if not batch_field:
		return []
	filters = {"academic_year": academic_year, batch_field: student_batch}
	if "disabled" in fields:
		filters["disabled"] = 0
	query_fields = ["name"]
	if "course" in fields:
		query_fields.append("course")
	return frappe.get_all("Student Group", filters=filters, fields=query_fields, order_by="name asc")


def _course_group_map(academic_year, groups):
	mapping = defaultdict(set)
	group_names = [row.name for row in groups]
	for group in groups:
		if group.get("course"):
			mapping[group.course].add(group.name)

	if not group_names or not frappe.db.exists("DocType", "Course Schedule"):
		return mapping
	fields = _doctype_fields("Course Schedule")
	if not {"student_group", "course"}.issubset(fields):
		return mapping
	filters = {"student_group": ["in", group_names], "docstatus": ["<", 2]}
	if "academic_year" in fields:
		filters["academic_year"] = academic_year
	for row in frappe.get_all("Course Schedule", filters=filters, fields=["student_group", "course"]):
		if row.course:
			mapping[row.course].add(row.student_group)
	return mapping


def _department_for_course(course):
	fields = _doctype_fields("Course")
	if "department" in fields:
		return frappe.db.get_value("Course", course, "department")
	return None


def _same_group_names(requirement, group_names):
	return {row.student_group for row in requirement.affected_student_groups} == set(group_names)


def _set_affected_groups(requirement, group_names):
	existing = {row.student_group: row for row in requirement.affected_student_groups}
	requirement.set("affected_student_groups", [])
	for group_name in sorted(group_names):
		previous = existing.get(group_name)
		requirement.append(
			"affected_student_groups",
			{
				"student_group": group_name,
				"assessment_plan": previous.assessment_plan if previous else None,
				"plan_status": previous.plan_status if previous else "Missing",
			},
		)


def generate_exam_paper_requirements(cycle):
	if not cycle.student_batches:
		frappe.throw(_("Add at least one Student Batch before generating paper requirements."))

	selected_courses = [row.course for row in cycle.courses]
	created = 0
	updated = 0
	without_groups = 0
	hod_by_department = {row.department: row.hod_user for row in cycle.hod_assignments}

	for batch_row in cycle.student_batches:
		groups = _student_groups_for_batch(cycle.academic_year, batch_row.student_batch)
		course_groups = _course_group_map(cycle.academic_year, groups)
		courses = selected_courses if cycle.course_selection_policy == "Selected Courses" else sorted(course_groups)
		if not courses:
			frappe.throw(
				_("No scheduled Courses were found for Student Batch {0}. Use Selected Courses or prepare Course Schedules first.").format(
					batch_row.student_batch
				)
			)

		for course in courses:
			group_names = sorted(course_groups.get(course, set()))
			without_groups += int(not group_names)
			department = _department_for_course(course)
			mapped_hod = hod_by_department.get(department)
			name = frappe.db.get_value(
				"Exam Paper Requirement",
				{
					"examination_cycle": cycle.name,
					"student_batch": batch_row.student_batch,
					"course": course,
				},
			)
			if name:
				requirement = frappe.get_doc("Exam Paper Requirement", name)
				changed = False
				if not _same_group_names(requirement, group_names):
					_set_affected_groups(requirement, group_names)
					requirement.add_activity("Affected Student Groups refreshed")
					changed = True
				if department and requirement.department != department:
					requirement.department = department
					changed = True
				if mapped_hod and requirement.hod_user != mapped_hod:
					requirement.hod_user = mapped_hod
					changed = True
				if changed:
					requirement.save(ignore_permissions=True)
				updated += 1
				continue

			requirement = frappe.new_doc("Exam Paper Requirement")
			requirement.examination_cycle = cycle.name
			requirement.student_batch = batch_row.student_batch
			requirement.course = course
			requirement.department = department
			requirement.hod_user = mapped_hod
			_set_affected_groups(requirement, group_names)
			requirement.add_activity("Requirement generated")
			requirement.insert(ignore_permissions=True)
			created += 1

	cycle.db_set("status", "Requirements Generated", update_modified=True)
	return {"created": created, "updated": updated, "without_groups": without_groups}


def _is_manager(user=None):
	return bool(set(frappe.get_roles(user)) & MANAGER_ROLES)


def get_requirement_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if not user or user == "Administrator" or _is_manager(user):
		return ""
	escaped = frappe.db.escape(user)
	return """(
		`tabExam Paper Requirement`.`hod_user` = {user}
		or `tabExam Paper Requirement`.`lead_teacher_user` = {user}
		or exists (
			select 1 from `tabExam Paper Collaborator` collaborator
			where collaborator.parent = `tabExam Paper Requirement`.name
			and collaborator.parenttype = 'Exam Paper Requirement'
			and collaborator.user = {user}
		)
	)""".format(user=escaped)


def has_requirement_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator" or _is_manager(user):
		return True
	allowed = user in {doc.hod_user, doc.lead_teacher_user} or user in {row.user for row in doc.collaborators}
	if not allowed:
		return False
	if permission_type in {"create", "delete", "submit", "cancel", "amend"}:
		return False
	return True


def create_exam_notification(user, subject, requirement, reminder_key=None):
	if not user or user in {"Guest", "Administrator"}:
		return
	key = reminder_key or "workflow"
	full_subject = "{0}: {1}".format(subject, requirement.requirement_title)[:140]
	if frappe.db.exists(
		"Notification Log",
		{
			"for_user": user,
			"document_type": "Exam Paper Requirement",
			"document_name": requirement.name,
			"subject": full_subject,
			"creation": [">=", nowdate()],
		},
	):
		return
	try:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": full_subject,
				"email_content": _("Open Exam Paper Requirement {0} to take action. Reminder: {1}.").format(
					requirement.name, key
				),
				"for_user": user,
				"type": "Alert",
				"document_type": "Exam Paper Requirement",
				"document_name": requirement.name,
				"from_user": frappe.session.user if frappe.session.user != "Guest" else "Administrator",
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Exam preparation notification failed")


def get_exam_management_alerts(examination_cycle=None):
	filters = {"status": ["!=", "Complete"]}
	if examination_cycle:
		filters["examination_cycle"] = examination_cycle
	rows = frappe.get_all(
		"Exam Paper Requirement",
		filters=filters,
		fields=[
			"name",
			"requirement_title",
			"status",
			"hod_user",
			"lead_teacher_user",
			"assignment_deadline",
			"paper_submission_deadline",
			"hod_review_deadline",
			"admin_approval_deadline",
			"exam_start_date",
			"expected_plan_count",
			"missing_plan_count",
		],
	)
	today = getdate(nowdate())
	managers = get_enabled_users_with_role("Education Manager")
	alerts = []

	def add(row, kind, severity, due_date, users, message):
		days_remaining = date_diff(getdate(due_date), today) if due_date else None
		alerts.append(
			{
				"alert_key": "{0}:{1}".format(kind, row.name),
				"kind": kind,
				"severity": severity,
				"requirement": row.name,
				"title": row.requirement_title,
				"status": row.status,
				"due_date": due_date,
				"days_remaining": days_remaining,
				"users": sorted({user for user in users if user}),
				"message": message,
			}
		)

	for row in rows:
		if not row.expected_plan_count:
			severity = "Critical" if getdate(row.admin_approval_deadline) < today else "Warning"
			add(
				row,
				"student-group-mapping-missing",
				severity,
				row.admin_approval_deadline,
				managers,
				_("No affected Student Groups are mapped, so Assessment Plans cannot be generated."),
			)
		if not row.lead_teacher_user:
			severity = "Critical" if getdate(row.assignment_deadline) < today else "Warning"
			add(row, "unassigned-paper", severity, row.assignment_deadline, [row.hod_user] + managers, _("No lead teacher has been assigned."))
		elif row.status in {"Assigned", "In Preparation", "Changes Requested"}:
			severity = "Critical" if getdate(row.paper_submission_deadline) < today else "Warning"
			add(row, "paper-not-submitted", severity, row.paper_submission_deadline, [row.lead_teacher_user, row.hod_user], _("The required paper has not been submitted to the HOD."))
		elif row.status == "Submitted to HOD":
			severity = "Critical" if getdate(row.hod_review_deadline) < today else "Warning"
			add(row, "hod-review-pending", severity, row.hod_review_deadline, [row.hod_user], _("HOD review is pending."))
		elif row.status == "Submitted to Exam Administration":
			severity = "Critical" if getdate(row.admin_approval_deadline) < today else "Warning"
			add(row, "admin-approval-pending", severity, row.admin_approval_deadline, managers, _("Final examination-office approval is pending."))
		elif row.status in APPROVED_STATUSES and row.missing_plan_count:
			severity = "Critical" if date_diff(getdate(row.exam_start_date), today) <= 7 else "Warning"
			add(row, "assessment-plans-missing", severity, row.exam_start_date, managers, _("Approved paper still has missing Assessment Plans."))
	return alerts


def get_exam_preparation_summary(examination_cycle=None):
	"""Stable service for future MIS/Executive Dashboard integration."""
	filters = {"examination_cycle": examination_cycle} if examination_cycle else {}
	rows = frappe.get_all(
		"Exam Paper Requirement",
		filters=filters,
		fields=["status", "expected_plan_count", "missing_plan_count"],
	)
	by_status = defaultdict(int)
	for row in rows:
		by_status[row.status] += 1
	alerts = get_exam_management_alerts(examination_cycle)
	return {
		"total_requirements": len(rows),
		"by_status": dict(by_status),
		"overdue": len([row for row in alerts if row.get("days_remaining") is not None and row["days_remaining"] < 0]),
		"critical": len([row for row in alerts if row["severity"] == "Critical"]),
		"missing_assessment_plans": sum(row.missing_plan_count or 0 for row in rows),
		"missing_group_mappings": len([row for row in rows if not row.get("expected_plan_count")]),
	}


def send_exam_preparation_reminders():
	for alert in get_exam_management_alerts():
		days = alert.get("days_remaining")
		if days not in {7, 2, 0, -1, -3, -7}:
			continue
		requirement = frappe.get_doc("Exam Paper Requirement", alert["requirement"])
		for user in alert["users"]:
			create_exam_notification(
				user,
				alert["message"],
				requirement,
				reminder_key="{0}:{1}".format(alert["kind"], days),
			)


def refresh_requirements_for_assessment_plan(doc, method=None):
	if not doc.get("student_group") or not doc.get("course") or not doc.get("assessment_group"):
		return
	parent_names = [
		row.parent
		for row in frappe.get_all(
			"Exam Paper Affected Group",
			filters={
				"parenttype": "Exam Paper Requirement",
				"parentfield": "affected_student_groups",
				"student_group": doc.student_group,
			},
			fields=["parent"],
		)
	]
	if not parent_names:
		return
	matching = frappe.get_all(
		"Exam Paper Requirement",
		filters={
			"name": ["in", parent_names],
			"academic_year": doc.academic_year,
			"assessment_group": doc.assessment_group,
			"course": doc.course,
		},
		pluck="name",
	)
	for name in matching:
		requirement = frappe.get_doc("Exam Paper Requirement", name)
		requirement.update_plan_coverage()
		requirement.flags.in_workflow_action = True
		requirement.save(ignore_permissions=True)
