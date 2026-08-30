import frappe
from frappe import _
from frappe.utils import cint, date_diff, getdate, nowdate


MANAGER_ROLES = {"System Manager", "Education Manager"}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	query_filters = {}
	for fieldname in (
		"examination_cycle",
		"assessment_type",
		"school_term",
		"assessment_group",
		"course",
		"student_group",
		"responsible_user",
		"status",
	):
		if filters.get(fieldname):
			query_filters[fieldname] = filters.get(fieldname)

	user = frappe.session.user
	is_manager = user == "Administrator" or bool(set(frappe.get_roles(user)) & MANAGER_ROLES)

	rows = frappe.get_all(
		"Assessment Result Submission Tracker",
		filters=query_filters,
		fields=[
			"name",
			"assessment_plan",
			"examination_cycle",
			"assessment_type",
			"school_term",
			"assessment_group",
			"course",
			"student_group",
			"instructor",
			"responsible_user",
			"hod_user",
			"assessment_date",
			"result_due_date",
			"expected_student_count",
			"draft_result_count",
			"submitted_result_count",
			"non_participation_count",
			"missing_result_count",
			"completion_percentage",
			"status",
			"instructor_mapping_issue",
		],
		order_by="result_due_date asc, student_group asc, course asc",
	)

	today = getdate(nowdate())
	result = []
	for row in rows:
		if not is_manager and user not in {row.responsible_user, row.hod_user}:
			continue
		row.overdue_days = (
			max(0, date_diff(today, getdate(row.result_due_date)))
			if row.result_due_date and row.status != "Results Complete"
			else 0
		)
		if cint(filters.overdue_only) and row.status != "Overdue":
			continue
		if cint(filters.missing_results_only) and not row.missing_result_count:
			continue
		result.append(row)
	summary = [
		{"label": _("Tracked Plans"), "value": len(result), "indicator": "Blue", "datatype": "Int"},
		{
			"label": _("Results Complete"),
			"value": len([row for row in result if row.status == "Results Complete"]),
			"indicator": "Green",
			"datatype": "Int",
		},
		{
			"label": _("Overdue"),
			"value": len([row for row in result if row.status == "Overdue"]),
			"indicator": "Red",
			"datatype": "Int",
		},
		{
			"label": _("Unresolved Students"),
			"value": sum(row.missing_result_count or 0 for row in result),
			"indicator": "Orange",
			"datatype": "Int",
		},
		{
			"label": _("Instructor Mapping Errors"),
			"value": len([row for row in result if row.status == "Instructor Mapping Error"]),
			"indicator": "Red",
			"datatype": "Int",
		},
	]
	return get_columns(), result, None, None, summary


def get_columns():
	return [
		{"fieldname": "assessment_type", "label": _("Type"), "fieldtype": "Data", "width": 125},
		{"fieldname": "course", "label": _("Course"), "fieldtype": "Link", "options": "Course", "width": 180},
		{"fieldname": "student_group", "label": _("Student Group"), "fieldtype": "Link", "options": "Student Group", "width": 150},
		{"fieldname": "instructor", "label": _("Scheduled Instructor"), "fieldtype": "Link", "options": "Instructor", "width": 160},
		{"fieldname": "responsible_user", "label": _("Teacher User"), "fieldtype": "Link", "options": "User", "width": 190},
		{"fieldname": "assessment_date", "label": _("Assessment Date"), "fieldtype": "Date", "width": 115},
		{"fieldname": "result_due_date", "label": _("Results Due"), "fieldtype": "Date", "width": 110},
		{"fieldname": "expected_student_count", "label": _("Expected"), "fieldtype": "Int", "width": 80},
		{"fieldname": "draft_result_count", "label": _("Draft"), "fieldtype": "Int", "width": 70},
		{"fieldname": "submitted_result_count", "label": _("Submitted"), "fieldtype": "Int", "width": 90},
		{"fieldname": "non_participation_count", "label": _("Did Not Sit / Exempt"), "fieldtype": "Int", "width": 125},
		{"fieldname": "missing_result_count", "label": _("Unresolved"), "fieldtype": "Int", "width": 90},
		{"fieldname": "completion_percentage", "label": _("Completion"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 150},
		{"fieldname": "overdue_days", "label": _("Overdue Days"), "fieldtype": "Int", "width": 100},
		{"fieldname": "assessment_plan", "label": _("Assessment Plan"), "fieldtype": "Link", "options": "Assessment Plan", "width": 180},
		{"fieldname": "name", "label": _("Tracker"), "fieldtype": "Link", "options": "Assessment Result Submission Tracker", "width": 165},
	]
