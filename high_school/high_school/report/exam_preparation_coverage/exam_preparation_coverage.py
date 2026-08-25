import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"fieldname": "requirement", "label": _("Requirement"), "fieldtype": "Link", "options": "Exam Paper Requirement", "width": 145},
		{"fieldname": "student_batch", "label": _("Form / Batch"), "fieldtype": "Link", "options": "Student Batch Name", "width": 140},
		{"fieldname": "course", "label": _("Course"), "fieldtype": "Link", "options": "Course", "width": 170},
		{"fieldname": "department", "label": _("Department"), "fieldtype": "Link", "options": "Department", "width": 130},
		{"fieldname": "hod_user", "label": _("HOD"), "fieldtype": "Link", "options": "User", "width": 150},
		{"fieldname": "lead_teacher_user", "label": _("Lead Teacher"), "fieldtype": "Link", "options": "User", "width": 160},
		{"fieldname": "status", "label": _("Paper Status"), "fieldtype": "Data", "width": 180},
		{"fieldname": "current_deadline", "label": _("Current Deadline"), "fieldtype": "Date", "width": 115},
		{"fieldname": "days_remaining", "label": _("Days Left"), "fieldtype": "Int", "width": 80},
		{"fieldname": "blueprint", "label": _("Blueprint"), "fieldtype": "Data", "width": 85},
		{"fieldname": "question_paper", "label": _("Paper"), "fieldtype": "Data", "width": 75},
		{"fieldname": "marking_scheme", "label": _("Scheme"), "fieldtype": "Data", "width": 75},
		{"fieldname": "group_mapping", "label": _("Group Mapping"), "fieldtype": "Data", "width": 105},
		{"fieldname": "expected_plans", "label": _("Expected Plans"), "fieldtype": "Int", "width": 105},
		{"fieldname": "created_plans", "label": _("Created"), "fieldtype": "Int", "width": 75},
		{"fieldname": "missing_plans", "label": _("Missing"), "fieldtype": "Int", "width": 75},
	]


def _deadline_for(row):
	if row.status == "Awaiting Assignment":
		return row.assignment_deadline
	if row.status in {"Assigned", "In Preparation", "Changes Requested"}:
		return row.paper_submission_deadline
	if row.status == "Submitted to HOD":
		return row.hod_review_deadline
	if row.status == "Submitted to Exam Administration":
		return row.admin_approval_deadline
	if row.missing_plan_count:
		return row.exam_start_date
	return None


def get_data(filters):
	db_filters = {}
	for fieldname in ("examination_cycle", "status", "department", "student_batch", "lead_teacher_user"):
		if filters.get(fieldname):
			db_filters[fieldname] = filters.get(fieldname)
	rows = frappe.get_list(
		"Exam Paper Requirement",
		filters=db_filters,
		fields=[
			"name",
			"student_batch",
			"course",
			"department",
			"hod_user",
			"lead_teacher_user",
			"status",
			"assignment_deadline",
			"paper_submission_deadline",
			"hod_review_deadline",
			"admin_approval_deadline",
			"exam_start_date",
			"blueprint_file",
			"question_paper_file",
			"marking_scheme_file",
			"expected_plan_count",
			"created_plan_count",
			"missing_plan_count",
		],
		order_by="student_batch asc, course asc",
	)
	today = getdate(nowdate())
	data = []
	for row in rows:
		deadline = _deadline_for(row)
		days_remaining = date_diff(getdate(deadline), today) if deadline else None
		if filters.get("overdue_only") and (days_remaining is None or days_remaining >= 0):
			continue
		if filters.get("missing_plans_only") and not row.missing_plan_count:
			continue
		data.append(
			{
				"requirement": row.name,
				"student_batch": row.student_batch,
				"course": row.course,
				"department": row.department,
				"hod_user": row.hod_user,
				"lead_teacher_user": row.lead_teacher_user,
				"status": row.status,
				"current_deadline": deadline,
				"days_remaining": days_remaining,
				"blueprint": _("Received") if row.blueprint_file else _("Missing"),
				"question_paper": _("Received") if row.question_paper_file else _("Missing"),
				"marking_scheme": _("Received") if row.marking_scheme_file else _("Missing"),
				"group_mapping": _("Mapped") if row.expected_plan_count else _("Missing"),
				"expected_plans": row.expected_plan_count,
				"created_plans": row.created_plan_count,
				"missing_plans": row.missing_plan_count,
			}
		)
	return data
