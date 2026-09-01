from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import flt


MANAGER_ROLES = ("Education Manager", "System Manager")


def _as_list(value):
	if not value:
		return []
	if isinstance(value, str):
		return json.loads(value)
	return value


def _meta_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _first_available(fields, *names):
	return next((name for name in names if name in fields), None)


def _validate_school_term(school_term, academic_year):
	term_year = frappe.db.get_value("School Term", school_term, "academic_year")
	if term_year and term_year != academic_year:
		frappe.throw(
			_("School Term {0} belongs to Academic Year {1}, not {2}.").format(
				school_term, term_year, academic_year
			)
		)


def _period_name(school_term, student_group):
	return "{0} - {1}".format(school_term, student_group)


def _active_student_count(student_group):
	fields = _meta_fields("Student Group Student")
	filters = {"parent": student_group, "parenttype": "Student Group"}
	if "active" in fields:
		filters["active"] = 1
	return frappe.db.count("Student Group Student", filters)


def _existing_period(academic_year, school_term, student_group):
	return frappe.db.get_value(
		"School Performance Period",
		{
			"academic_year": academic_year,
			"school_term": school_term,
			"main_student_group": student_group,
		},
	)


def _main_group_filters(academic_year, program=None, student_batch=None):
	fields = _meta_fields("Student Group")
	filters = {"academic_year": academic_year}
	if "disabled" in fields:
		filters["disabled"] = 0
	if "group_based_on" in fields:
		filters["group_based_on"] = "Batch"
	if program and "program" in fields:
		filters["program"] = program
	batch_field = _first_available(fields, "student_batch", "student_batch_name", "batch")
	if student_batch and batch_field:
		filters[batch_field] = student_batch
	return filters, batch_field


def get_main_group_coverage(academic_year, school_term):
	"""Return coverage of active Batch-based main groups by performance periods."""
	group_fields = _meta_fields("Student Group")
	filters, batch_field = _main_group_filters(academic_year)
	query_fields = ["name"]
	if batch_field and batch_field not in query_fields:
		query_fields.append(batch_field)

	groups = frappe.get_all(
		"Student Group",
		filters=filters,
		fields=query_fields,
		order_by="name asc",
	)
	expected = []
	for group in groups:
		student_count = _active_student_count(group.name)
		if not student_count:
			continue
		expected.append(
			{
				"student_group": group.name,
				"student_batch": group.get(batch_field) if batch_field else None,
				"student_count": student_count,
			}
		)

	periods = frappe.get_all(
		"School Performance Period",
		filters={
			"academic_year": academic_year,
			"school_term": school_term,
		},
		fields=["name", "main_student_group"],
	)
	period_by_group = {
		row.main_student_group: row.name
		for row in periods
		if row.main_student_group
	}
	covered = []
	missing = []
	for group in expected:
		item = {
			**group,
			"performance_period": period_by_group.get(group["student_group"]),
		}
		(covered if item["performance_period"] else missing).append(item)

	return {
		"complete": bool(expected) and not missing,
		"expected_group_count": len(expected),
		"covered_group_count": len(covered),
		"missing_group_count": len(missing),
		"covered_groups": covered,
		"missing_groups": missing,
		"detection_reliable": "group_based_on" in group_fields and bool(batch_field),
	}


@frappe.whitelist()
def get_main_group_candidates(academic_year, school_term, program=None, student_batch=None):
	frappe.only_for(MANAGER_ROLES)
	_validate_school_term(school_term, academic_year)

	group_fields = _meta_fields("Student Group")
	filters, batch_field = _main_group_filters(academic_year, program, student_batch)
	query_fields = ["name"]
	for fieldname in ("student_group_name", "program", batch_field):
		if fieldname and fieldname in group_fields and fieldname not in query_fields:
			query_fields.append(fieldname)

	groups = frappe.get_all(
		"Student Group",
		filters=filters,
		fields=query_fields,
		order_by="name asc",
	)
	rows = []
	for group in groups:
		existing = _existing_period(academic_year, school_term, group.name)
		student_count = _active_student_count(group.name)
		rows.append(
			{
				"create_period": 0 if existing or not student_count else 1,
				"student_group": group.name,
				"student_batch": group.get(batch_field) if batch_field else None,
				"student_count": student_count,
				"existing_period": existing,
			}
		)

	detection = _(
		"Only Student Groups based on Batch are shown. These are treated as main/home groups; Course-based option groups are excluded."
	)
	if "group_based_on" not in group_fields:
		detection = _(
			"This Education version has no Group Based On field. Review the candidates carefully and select only main/home Student Groups."
		)
	return {"rows": rows, "message": detection}


def _validate_components(components):
	components = _as_list(components)
	if not components:
		frappe.throw(_("Add at least one assessment component."))

	cleaned = []
	seen = set()
	for row in components:
		assessment_group = row.get("assessment_group")
		weight = flt(row.get("weight"))
		if not assessment_group:
			frappe.throw(_("Every component must select an Assessment Group."))
		if assessment_group in seen:
			frappe.throw(_("Assessment Group {0} is listed more than once.").format(assessment_group))
		if weight <= 0:
			frappe.throw(_("Every component weight must be greater than zero."))
		seen.add(assessment_group)
		cleaned.append({"assessment_group": assessment_group, "weight": weight})

	total = sum(row["weight"] for row in cleaned)
	if abs(total - 100) > 0.001:
		frappe.throw(_("Assessment component weights must total 100%. Current total: {0}%.").format(total))
	return cleaned


def _selected_groups(rows):
	selected = []
	seen = set()
	for row in _as_list(rows):
		if not int(row.get("create_period") or 0):
			continue
		student_group = row.get("student_group")
		if not student_group:
			frappe.throw(_("Every selected row must contain a Student Group."))
		if student_group in seen:
			frappe.throw(_("Student Group {0} is selected more than once.").format(student_group))
		seen.add(student_group)
		selected.append(student_group)
	if not selected:
		frappe.throw(_("Select at least one main Student Group."))
	return selected


def _validate_settings(settings):
	settings = frappe._dict(json.loads(settings) if isinstance(settings, str) else settings)
	for fieldname in ("academic_year", "school_term", "result_status_filter", "missing_result_policy", "tie_method"):
		if not settings.get(fieldname):
			frappe.throw(_("{0} is required.").format(fieldname.replace("_", " ").title()))
	settings.minimum_subjects = int(settings.get("minimum_subjects") or 0)
	settings.rounding_precision = int(settings.get("rounding_precision") or 0)
	if settings.minimum_subjects < 1:
		frappe.throw(_("Minimum Subjects Required must be at least 1."))
	if settings.rounding_precision < 0 or settings.rounding_precision > 4:
		frappe.throw(_("Displayed Decimal Places must be between 0 and 4."))
	_validate_school_term(settings.school_term, settings.academic_year)
	return settings


@frappe.whitelist()
def create_performance_periods(settings, rows, components):
	frappe.only_for(MANAGER_ROLES)
	settings = _validate_settings(settings)
	components = _validate_components(components)
	student_groups = _selected_groups(rows)
	group_fields = _meta_fields("Student Group")

	created = []
	skipped = []
	for student_group in student_groups:
		group = frappe.db.get_value(
			"Student Group",
			student_group,
			["academic_year"] + (["group_based_on"] if "group_based_on" in group_fields else []),
			as_dict=True,
		)
		if not group:
			frappe.throw(_("Student Group {0} does not exist.").format(student_group))
		if group.academic_year and group.academic_year != settings.academic_year:
			frappe.throw(
				_("Student Group {0} belongs to Academic Year {1}, not {2}.").format(
					student_group, group.academic_year, settings.academic_year
				)
			)
		if group.get("group_based_on") and group.group_based_on != "Batch":
			frappe.throw(_("Student Group {0} is not a main Batch-based group.").format(student_group))

		existing = _existing_period(settings.academic_year, settings.school_term, student_group)
		if existing:
			skipped.append(existing)
			continue

		period_name = _period_name(settings.school_term, student_group)
		if frappe.db.exists("School Performance Period", period_name):
			frappe.throw(
				_("Performance Period name {0} already exists with different settings.").format(period_name)
			)

		doc = frappe.new_doc("School Performance Period")
		doc.update(
			{
				"period_name": period_name,
				"academic_year": settings.academic_year,
				"school_term": settings.school_term,
				"main_student_group": student_group,
				"result_status_filter": settings.result_status_filter,
				"missing_result_policy": settings.missing_result_policy,
				"tie_method": settings.tie_method,
				"minimum_subjects": settings.minimum_subjects,
				"rounding_precision": settings.rounding_precision,
			}
		)
		for component in components:
			doc.append("components", component)
		doc.insert()
		created.append(doc.name)

	return {"created": created, "skipped": skipped}
