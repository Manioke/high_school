from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt


def _meta_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _grade(score, scale):
	if not scale:
		return ""
	for row in frappe.get_all("Grading Scale Interval", filters={"parent": scale}, fields=["grade_code", "threshold"], order_by="threshold desc", limit_page_length=0):
		if flt(score) >= flt(row.threshold):
			return row.grade_code or ""
	return ""


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.academic_year or not filters.program:
		frappe.throw(_("Academic Year and Program are required."))

	group_fields = _meta_fields("Student Group")
	batch_field = next((name for name in ("student_batch_name", "student_batch", "batch") if name in group_fields), None)
	group_filters = {}
	if "program" in group_fields:
		group_filters["program"] = filters.program
	if "academic_year" in group_fields:
		group_filters["academic_year"] = filters.academic_year
	if filters.student_batch and batch_field:
		group_filters[batch_field] = filters.student_batch
	if filters.student_group:
		group_filters["name"] = filters.student_group

	query = {"academic_year": filters.academic_year, "docstatus": 1, "status": "Complete"}
	if filters.school_term:
		query["school_term"] = filters.school_term

	show_group_breakdown = bool(filters.student_batch or filters.student_group)
	if show_group_breakdown:
		group_rows = frappe.get_all(
			"Student Group",
			filters=group_filters,
			fields=["name"] + ([f"{batch_field} as student_batch"] if batch_field else []),
			order_by="name asc",
			limit_page_length=0,
		)
		group_names = [row.name for row in group_rows]
		if not group_names:
			return _columns(), [], _("No Student Groups match the selected Program, Academic Year and Student Batch."), None
		query["main_student_group"] = ["in", group_names]
		summaries = frappe.get_all("Student Performance Summary", filters=query, fields=["name", "student", "main_student_group", "overall_percentage"], limit_page_length=0)
	else:
		summaries = frappe.get_all("Student Performance Summary", filters=query, fields=["name", "student", "main_student_group", "overall_percentage"], limit_page_length=0)
		groups = sorted({row.main_student_group for row in summaries if row.main_student_group})
		if groups:
			group_filters["name"] = ["in", groups]
			group_rows = frappe.get_all(
				"Student Group",
				filters=group_filters,
				fields=["name"] + ([f"{batch_field} as student_batch"] if batch_field else []),
				limit_page_length=0,
			)
		else:
			group_rows = []

	batch_by_group = {row.name: row.get("student_batch") for row in group_rows}
	allowed_groups = set(batch_by_group)
	aggregates, students = defaultdict(list), defaultdict(set)
	for row in summaries:
		if row.main_student_group not in allowed_groups:
			continue
		batch = batch_by_group.get(row.main_student_group) or _("Unassigned")
		key = (batch, row.main_student_group) if show_group_breakdown else (batch, None)
		aggregates[key].append(flt(row.overall_percentage))
		students[key].add(row.student)

	if show_group_breakdown:
		for row in group_rows:
			aggregates.setdefault((row.get("student_batch") or _("Unassigned"), row.name), [])

	target = flt(frappe.db.get_single_value("School MIS Settings", "academic_performance_target") or 60)
	data = []
	for (batch, group), scores in sorted(aggregates.items()):
		average = sum(scores) / len(scores) if scores else None
		data.append({
			"student_batch": batch,
			"student_group": group,
			"students": len(students[(batch, group)]),
			"average": average,
			"grade": _grade(average, filters.grading_scale) if average is not None else "",
			"highest": max(scores) if scores else None,
			"lowest": min(scores) if scores else None,
			"target": target,
			"variance": average - target if average is not None else None,
			"target_status": (_("Met") if average >= target else _("Below")) if average is not None else _("No Data"),
		})
	chart = {"data": {"labels": [row["student_group"] or row["student_batch"] for row in data], "datasets": [{"name": _("Average %"), "values": [row["average"] or 0 for row in data]}, {"name": _("Target %"), "values": [target for row in data]}]}, "type": "bar"}
	message = _("The selected Student Batch is expanded into its associated Student Groups. Groups without a completed official Student Performance Summary are shown as No Data.") if show_group_breakdown else _("Each Batch average is the mean of official submitted, complete Student Performance Summary overall percentages. Select a Student Batch to expand it into Student Groups.")
	return _columns(), data, message, chart


def _columns():
	return [
		{"fieldname":"student_batch","label":_("Student Batch"),"fieldtype":"Link","options":"Student Batch Name","width":180},
		{"fieldname":"student_group","label":_("Student Group"),"fieldtype":"Link","options":"Student Group","width":180},
		{"fieldname":"students","label":_("Students"),"fieldtype":"Int","width":85},
		{"fieldname":"average","label":_("Average %"),"fieldtype":"Percent","width":110},
		{"fieldname":"grade","label":_("Average Grade"),"fieldtype":"Data","width":110},
		{"fieldname":"highest","label":_("Highest %"),"fieldtype":"Percent","width":105},
		{"fieldname":"lowest","label":_("Lowest %"),"fieldtype":"Percent","width":105},
		{"fieldname":"target","label":_("Target %"),"fieldtype":"Percent","width":100},
		{"fieldname":"variance","label":_("Vs Target"),"fieldtype":"Percent","width":100},
		{"fieldname":"target_status","label":_("Status"),"fieldtype":"Data","width":90},
	]
