import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.performance_period:
		frappe.throw(_("Performance Period is required."))

	query_filters = {
		"performance_period": filters.performance_period,
		"docstatus": ["<", 2],
	}
	if not filters.include_incomplete:
		query_filters["status"] = "Complete"

	rows = frappe.get_all(
		"Student Performance Summary",
		filters=query_filters,
		fields=[
			"name",
			"position",
			"student",
			"student_name",
			"overall_percentage",
			"total_subjects",
			"status",
			"rank_out_of",
			"docstatus",
		],
		order_by="position asc, overall_percentage desc, student_name asc",
	)

	top_n = cint(filters.top_n)
	if top_n > 0:
		rows = [row for row in rows if not row.position or row.position <= top_n]

	return get_columns(), rows


def get_columns():
	return [
		{"fieldname": "position", "label": _("Position"), "fieldtype": "Int", "width": 90},
		{"fieldname": "student", "label": _("Student"), "fieldtype": "Link", "options": "Student", "width": 140},
		{"fieldname": "student_name", "label": _("Student Name"), "fieldtype": "Data", "width": 220},
		{
			"fieldname": "overall_percentage",
			"label": _("Overall Percentage"),
			"fieldtype": "Percent",
			"width": 150,
		},
		{"fieldname": "total_subjects", "label": _("Subjects"), "fieldtype": "Int", "width": 90},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "rank_out_of", "label": _("Ranked Students"), "fieldtype": "Int", "width": 120},
		{
			"fieldname": "name",
			"label": _("Performance Summary"),
			"fieldtype": "Link",
			"options": "Student Performance Summary",
			"width": 180,
		},
	]
