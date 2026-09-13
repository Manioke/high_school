"""Core Program Enrollment validation and balanced Student Group allocation."""

import random

import frappe
from frappe import _


def _meta_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _first_field(fields, *names):
	return next((name for name in names if name in fields), None)


def _batch_groups(doc):
	fields = _meta_fields("Student Group")
	batch_field = _first_field(fields, "student_batch_name", "student_batch", "batch")
	if not batch_field or "student_category" not in fields:
		frappe.throw(
			_("Student Group must expose Student Batch and Student Category fields before categories can be assigned automatically.")
		)

	filters = {batch_field: doc.student_batch_name, "academic_year": doc.academic_year}
	if doc.get("program") and "program" in fields:
		filters["program"] = doc.program
	if "disabled" in fields:
		filters["disabled"] = 0
	if "group_based_on" in fields:
		filters["group_based_on"] = "Batch"

	query_fields = ["name", "student_category"]
	if "max_strength" in fields:
		query_fields.append("max_strength")
	groups = frappe.get_all(
		"Student Group",
		filters=filters,
		fields=query_fields,
		order_by="name asc",
		limit_page_length=0,
	)
	category_keys = [group.get("student_category") or "" for group in groups]
	duplicates = sorted({key for key in category_keys if category_keys.count(key) > 1})
	if duplicates:
		labels = [_('blank Student Category') if not key else key for key in duplicates]
		frappe.throw(
			_("Student Groups for Program {0}, Batch {1}, and Academic Year {2} must each have a unique Student Category. Duplicate allocation key(s): {3}.").format(
				doc.get("program") or _("Not set"), doc.student_batch_name, doc.academic_year, ", ".join(labels)
			)
		)
	return groups


def _enrolled_category_count(doc, category):
	filters = {
		"academic_year": doc.academic_year,
		"student_batch_name": doc.student_batch_name,
		"docstatus": ["<", 2],
	}
	if doc.get("program"):
		filters["program"] = doc.program
	filters["student_category"] = category if category else ["is", "not set"]
	if doc.name and not doc.is_new():
		filters["name"] = ["!=", doc.name]
	return frappe.db.count("Program Enrollment", filters)


def _group_usage(doc, group):
	enrolled = _enrolled_category_count(doc, group.get("student_category"))
	active_members = frappe.db.count("Student Group Student", {"parent": group.name, "active": 1})
	return max(enrolled, active_members)


def _validate_group_capacity(doc, group):
	maximum = int(group.get("max_strength") or 0)
	used = _group_usage(doc, group)
	if maximum and used >= maximum:
		frappe.throw(
			_("Student Group {0} is full ({1} of {2}). Select another available group/category.").format(
				group.name, used, maximum
			),
			title=_("Student Group Capacity Reached"),
		)


def assign_available_student_category(doc, method=None):
	"""Validate or assign a category when a Program Enrollment is submitted."""
	if not doc.get("student_batch_name") or not doc.get("academic_year") or not doc.get("program"):
		frappe.throw(
			_("Program, Student Batch, and Academic Year are required before a Student Group can be assigned automatically."),
			title=_("Student Category Not Assigned"),
		)

	batch_program = frappe.db.get_value("Student Batch Name", doc.student_batch_name, "custom_program")
	if batch_program and batch_program != doc.program:
		frappe.throw(
			_("Student Batch {0} belongs to Program {1}, not {2}.").format(
				doc.student_batch_name, batch_program, doc.program
			)
		)

	groups = _batch_groups(doc)
	if not groups:
		frappe.throw(
			_("No active Batch-based Student Group is configured for Program {0}, Batch {1}, in {2}.").format(
				doc.program, doc.student_batch_name, doc.academic_year
			),
			title=_("Student Category Not Assigned"),
		)

	configured = {group.get("student_category") or "": group for group in groups}
	if doc.get("student_category"):
		if doc.student_category not in configured:
			frappe.throw(
				_("Student Category {0} is not configured for Program {1}, Batch {2}, in {3}.").format(
					doc.student_category, doc.program, doc.student_batch_name, doc.academic_year
				)
			)
		_validate_group_capacity(doc, configured[doc.student_category])
		return

	if len(groups) == 1:
		_validate_group_capacity(doc, groups[0])
		doc.student_category = groups[0].get("student_category")
		return

	automatic = frappe.db.get_single_value("School MIS Settings", "randomly_assign_student_category")
	automatic = True if automatic is None else bool(int(automatic))
	if not automatic:
		frappe.throw(
			_("Select a Student Category before submitting this Program Enrollment. Automatic group balancing is disabled in School MIS Settings."),
			title=_("Student Category Required"),
		)

	eligible = []
	full = []
	for group in groups:
		maximum = int(group.get("max_strength") or 0)
		used = _group_usage(doc, group)
		if maximum and used >= maximum:
			full.append({"group": group.name, "category": group.student_category, "used": used, "maximum": maximum})
		else:
			eligible.append((group, used))

	if not eligible:
		details = "<br>".join(
			_("{0} ({1}): {2} of {3}").format(row["group"], row["category"], row["used"], row["maximum"])
			for row in full
		)
		student = doc.get("student_name") or doc.get("student") or _("this student")
		frappe.throw(
			_("{0} could not be assigned because every category group for batch {1} is full.<br>{2}").format(
				student, doc.student_batch_name, details
			),
			title=_("All Student Groups Are Full"),
		)

	lowest = min(item[1] for item in eligible)
	chosen = random.SystemRandom().choice([item[0] for item in eligible if item[1] == lowest])
	doc.student_category = chosen.get("student_category")
