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
	parent_filters = {"academic_year": filters.academic_year, "docstatus": 1, "status": "Complete"}
	if filters.school_term:
		parent_filters["school_term"] = filters.school_term
	if filters.student_group:
		parent_filters["main_student_group"] = filters.student_group
	summaries = frappe.get_all("Student Performance Summary", filters=parent_filters, fields=["name", "student", "main_student_group"], limit_page_length=0)
	if not summaries:
		return _columns(), [], _("No submitted complete performance summaries match the filters.")

	group_fields = _meta_fields("Student Group")
	batch_field = next((name for name in ("student_batch_name", "student_batch", "batch") if name in group_fields), None)
	group_names = sorted({row.main_student_group for row in summaries if row.main_student_group})
	group_filters = {"name": ["in", group_names]}
	if filters.program and "program" in group_fields:
		group_filters["program"] = filters.program
	group_rows = frappe.get_all("Student Group", filters=group_filters, fields=["name"] + ([f"{batch_field} as student_batch"] if batch_field else []), limit_page_length=0)
	batch_by_group = {row.name: row.get("student_batch") for row in group_rows}
	if filters.program:
		summaries = [row for row in summaries if row.main_student_group in batch_by_group]
	if filters.student_batch:
		summaries = [row for row in summaries if batch_by_group.get(row.main_student_group) == filters.student_batch]
	if not summaries:
		return _columns(), [], _("No summaries belong to the selected Student Batch.")

	results = frappe.get_all("School Performance Course Result", filters={"parent": ["in", [row.name for row in summaries]], "status": "Complete"}, fields=["parent", "course", "percentage"], limit_page_length=0)
	summary_by_name = {row.name: row for row in summaries}
	courses = sorted({row.course for row in results})
	from high_school.high_school.exam_preparation import _department_for_course
	departments = {
		course: _department_for_course(course, filters.academic_year, group_names)[0]
		for course in courses
	}

	aggregates = defaultdict(list)
	students = defaultdict(set)
	for row in results:
		summary = summary_by_name.get(row.parent)
		department = departments.get(row.course) or _("Unassigned")
		if filters.department and department != filters.department:
			continue
		batch = batch_by_group.get(summary.main_student_group) or _("Unassigned")
		key = (department, row.course, batch, summary.main_student_group)
		aggregates[key].append(flt(row.percentage))
		students[key].add(summary.student)

	threshold = flt(frappe.db.get_single_value("School MIS Settings", "academic_intervention_threshold") or 50)
	data = []
	for key, scores in sorted(aggregates.items()):
		average = sum(scores) / len(scores)
		below = len([score for score in scores if score < threshold])
		data.append({
			"department": key[0], "course": key[1], "student_batch": key[2], "student_group": key[3],
			"students": len(students[key]), "average": average, "average_grade": _grade(average, filters.grading_scale),
			"highest": max(scores), "lowest": min(scores), "below_threshold": below,
			"below_rate": below / len(scores) * 100,
		})
	chart_rows = sorted(data, key=lambda row: row["average"], reverse=True)[:20]
	chart = {"data": {"labels": [f"{row['course']} — {row['student_group']}" for row in chart_rows], "datasets": [{"name": _("Average %"), "values": [row["average"] for row in chart_rows]}]}, "type": "bar"}
	return _columns(), data, _("Average course performance by Department and Student Group. Grade converts each group average through the selected Grading Scale."), chart


def _columns():
	return [
		{"fieldname":"department","label":_("Department"),"fieldtype":"Link","options":"Department","width":160},
		{"fieldname":"course","label":_("Course / Subject"),"fieldtype":"Link","options":"Course","width":210},
		{"fieldname":"student_batch","label":_("Student Batch"),"fieldtype":"Link","options":"Student Batch Name","width":150},
		{"fieldname":"student_group","label":_("Student Group / Stream"),"fieldtype":"Link","options":"Student Group","width":170},
		{"fieldname":"students","label":_("Students"),"fieldtype":"Int","width":80},
		{"fieldname":"average","label":_("Average %"),"fieldtype":"Percent","width":105},
		{"fieldname":"average_grade","label":_("Average Grade"),"fieldtype":"Data","width":110},
		{"fieldname":"highest","label":_("Highest %"),"fieldtype":"Percent","width":100},
		{"fieldname":"lowest","label":_("Lowest %"),"fieldtype":"Percent","width":100},
		{"fieldname":"below_threshold","label":_("Below Threshold"),"fieldtype":"Int","width":115},
		{"fieldname":"below_rate","label":_("Below %"),"fieldtype":"Percent","width":95},
	]
