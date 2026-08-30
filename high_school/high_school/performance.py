from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt

from high_school.high_school.performance_math import (
	MISSING_INCOMPLETE,
	assign_ranks,
	calculate_overall_percentage,
	calculate_weighted_percentage,
	rounded,
)


ASSESSMENT_RESULT_REQUIRED_FIELDS = {
	"assessment_plan",
	"student",
	"total_score",
	"maximum_score",
}


def validate_education_schema():
	fields = {field.fieldname for field in frappe.get_meta("Assessment Result").fields}
	missing = ASSESSMENT_RESULT_REQUIRED_FIELDS - fields
	if missing:
		frappe.throw(
			_("The installed Education app is missing Assessment Result fields required by High School: {0}").format(
				", ".join(sorted(missing))
			)
		)


def _get_group_students(student_group):
	return frappe.get_all(
		"Student Group Student",
		filters={"parent": student_group, "active": 1},
		fields=["student", "student_name"],
		order_by="idx asc",
	)


def _get_all_student_groups(students, academic_year):
	rows = frappe.get_all(
		"Student Group Student",
		filters={"student": ["in", students], "active": 1},
		fields=["student", "parent as student_group"],
	)

	group_names = list({row.student_group for row in rows})
	valid_groups = set()
	if group_names:
		valid_groups = {
			row.name
			for row in frappe.get_all(
				"Student Group",
				filters={"name": ["in", group_names], "academic_year": academic_year},
				fields=["name"],
			)
		}

	student_groups = defaultdict(set)
	for row in rows:
		if row.student_group in valid_groups:
			student_groups[row.student].add(row.student_group)
	return student_groups


def _get_assessment_plans(group_names, component_names, academic_year):
	if not group_names:
		return []
	return frappe.get_all(
		"Assessment Plan",
		filters={
			"student_group": ["in", list(group_names)],
			"assessment_group": ["in", component_names],
			"academic_year": academic_year,
			"docstatus": ["<", 2],
		},
		fields=["name", "student_group", "assessment_group", "course"],
	)


def _get_results(plan_names, students, submitted_only):
	if not plan_names:
		return []
	filters = {
		"assessment_plan": ["in", plan_names],
		"student": ["in", students],
		"docstatus": 1 if submitted_only else ["<", 2],
	}
	return frappe.get_all(
		"Assessment Result",
		filters=filters,
		fields=[
			"name",
			"assessment_plan",
			"student",
			"total_score",
			"maximum_score",
			"docstatus",
		],
		order_by="modified desc",
	)


def _result_percentage(result):
	maximum_score = flt(result.maximum_score)
	if maximum_score <= 0:
		frappe.throw(
			_("Assessment Result {0} must have a Maximum Score greater than zero.").format(result.name)
		)
	return flt(result.total_score) / maximum_score * 100


def build_performance(period):
	validate_education_schema()
	students = _get_group_students(period.main_student_group)
	if not students:
		frappe.throw(_("The selected main Student Group has no active students."))

	student_names = [row.student for row in students]
	student_groups = _get_all_student_groups(student_names, period.academic_year)
	all_groups = set().union(*student_groups.values()) if student_groups else set()
	component_weights = {row.assessment_group: flt(row.weight) for row in period.components}
	plans = _get_assessment_plans(all_groups, list(component_weights), period.academic_year)
	plan_by_name = {row.name: row for row in plans}

	results = _get_results(
		list(plan_by_name),
		student_names,
		period.result_status_filter == "Submitted Only",
	)
	results_by_key = defaultdict(list)
	for result in results:
		plan = plan_by_name.get(result.assessment_plan)
		if not plan or plan.student_group not in student_groups.get(result.student, set()):
			continue
		results_by_key[(result.student, plan.course, plan.assessment_group)].append(result)

	duplicates = [key for key, values in results_by_key.items() if len(values) > 1]
	if duplicates:
		sample = duplicates[0]
		frappe.throw(
			_("Multiple Assessment Results exist for student {0}, course {1}, and assessment {2}. Resolve the duplicates before calculating.").format(
				*sample
			)
		)

	plans_by_student = defaultdict(list)
	for plan in plans:
		for student in student_names:
			if plan.student_group in student_groups.get(student, set()):
				plans_by_student[student].append(plan)

	calculated = []
	for student_row in students:
		student = student_row.student
		courses = sorted({plan.course for plan in plans_by_student[student]})
		course_rows = []
		component_rows = []
		student_complete = True

		for course in courses:
			scores = []
			for assessment_group, weight in component_weights.items():
				matching_plans = [
					plan
					for plan in plans_by_student[student]
					if plan.course == course and plan.assessment_group == assessment_group
				]
				matching_results = results_by_key.get((student, course, assessment_group), [])
				result = matching_results[0] if matching_results else None
				present = bool(matching_plans and result)
				percentage = _result_percentage(result) if result else None
				scores.append({"percentage": percentage, "weight": weight, "present": present})
				component_rows.append(
					{
						"course": course,
						"assessment_group": assessment_group,
						"weight": weight,
						"assessment_plan": matching_plans[0].name if matching_plans else None,
						"assessment_result": result.name if result else None,
						"score": result.total_score if result else None,
						"maximum_score": result.maximum_score if result else None,
						"percentage": percentage,
						"status": "Complete" if present else "Missing",
					}
				)

			course_percentage, complete = calculate_weighted_percentage(scores, period.missing_result_policy)
			student_complete = student_complete and complete
			course_rows.append(
				{
					"course": course,
					"percentage": course_percentage,
					"status": "Complete" if complete else "Incomplete",
				}
			)

		minimum_met = len([row for row in course_rows if row["percentage"] is not None]) >= period.minimum_subjects
		student_complete = student_complete and minimum_met and bool(course_rows)
		overall = calculate_overall_percentage(row["percentage"] for row in course_rows)
		calculated.append(
			{
				"student": student,
				"student_name": student_row.student_name,
				"course_results": course_rows,
				"component_results": component_rows,
				"overall_percentage": overall,
				"is_complete": student_complete,
				"status": "Complete" if student_complete else "Incomplete",
			}
		)

	assign_ranks(calculated, period.tie_method)
	return calculated


def _save_summary(period, row):
	name = frappe.db.get_value(
		"Student Performance Summary",
		{"performance_period": period.name, "student": row["student"], "docstatus": ["<", 2]},
	)
	if name:
		doc = frappe.get_doc("Student Performance Summary", name)
		if doc.docstatus:
			return {"name": doc.name, "skipped": True}
		doc.set("course_results", [])
		doc.set("component_results", [])
	else:
		doc = frappe.new_doc("Student Performance Summary")

	doc.update(
		{
			"performance_period": period.name,
			"student": row["student"],
			"student_name": row["student_name"],
			"academic_year": period.academic_year,
			"school_term": period.school_term,
			"main_student_group": period.main_student_group,
			"status": row["status"],
			"total_subjects": len(row["course_results"]),
			"overall_percentage": rounded(row["overall_percentage"], period.rounding_precision),
			"position": row.get("rank"),
			"rank_out_of": row.get("rank_out_of"),
		}
	)
	for course_row in row["course_results"]:
		doc.append(
			"course_results",
			{
				**course_row,
				"percentage": rounded(course_row["percentage"], period.rounding_precision),
			},
		)
	for component_row in row["component_results"]:
		doc.append(
			"component_results",
			{
				**component_row,
				"percentage": rounded(component_row["percentage"], period.rounding_precision),
			},
		)
	return {"name": doc.save(ignore_permissions=True).name, "skipped": False}


@frappe.whitelist()
def generate_performance_summaries(performance_period):
	period = frappe.get_doc("School Performance Period", performance_period)
	period.check_permission("write")
	period.validate()
	protection_setting = frappe.db.get_single_value(
		"School MIS Settings", "protect_performance_summaries_until_results_complete"
	)
	if protection_setting is None or cint(protection_setting):
		from high_school.high_school.result_submission import get_performance_readiness

		readiness = get_performance_readiness(period)
		if not readiness["ready"]:
			sample = readiness["issues"][:10]
			details = "<br>".join(frappe.utils.escape_html(row["message"]) for row in sample)
			if readiness["issue_count"] > len(sample):
				details += "<br>" + _("...and {0} more issue(s).").format(
					readiness["issue_count"] - len(sample)
				)
			frappe.throw(
				_("Performance summaries are protected because {0} result-submission issue(s) remain.<br>{1}").format(
					readiness["issue_count"], details
				),
				title=_("Assessment Results Not Ready"),
			)
	if frappe.db.exists(
		"Student Performance Summary",
		{"performance_period": period.name, "docstatus": 1},
	):
		frappe.throw(
			_("This period has submitted performance summaries. Cancel them before recalculating so every student's rank remains consistent.")
		)
	rows = build_performance(period)
	results = [_save_summary(period, row) for row in rows]
	return {
		"created_or_updated": len([row for row in results if not row["skipped"]]),
		"skipped_submitted": len([row for row in results if row["skipped"]]),
		"total_students": len(results),
	}
