from __future__ import annotations

from collections import defaultdict
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint



def _meta_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _first_field(fields, *names):
	return next((name for name in names if name in fields), None)


def _term(doc):
	term = frappe.db.get_value(
		"School Term", doc.school_term, ["academic_year", "start_date", "end_date"], as_dict=True
	)
	if not term:
		frappe.throw(_("School Term {0} does not exist.").format(doc.school_term))
	if term.academic_year != doc.academic_year:
		frappe.throw(_("School Term {0} does not belong to Academic Year {1}.").format(doc.school_term, doc.academic_year))
	if not term.start_date or not term.end_date:
		frappe.throw(_("School Term {0} needs Start Date and End Date.").format(doc.school_term))
	return term


def _room_required():
	return cint(frappe.db.get_single_value("School MIS Settings", "require_rooms_for_timetable")) == 1


def _group_filters(doc):
	fields = _meta_fields("Student Group")
	filters = {"academic_year": doc.academic_year}
	if doc.get("program") and "program" in fields:
		filters["program"] = doc.program
	batch_field = _first_field(fields, "student_batch_name", "student_batch", "batch")
	if doc.student_batch and batch_field:
		filters[batch_field] = doc.student_batch
	if "disabled" in fields:
		filters["disabled"] = 0
	return fields, filters


def _form_level(value):
	match = re.search(r"\bform[\s_-]*(\d{1,2})\b", str(value or ""), re.IGNORECASE)
	return int(match.group(1)) if match else None


def _option_block(value):
	match = re.search(r"\bopt(?:ion)?[\s_-]*([1-4])\b", str(value or ""), re.IGNORECASE)
	return f"Opt{match.group(1)}" if match else None


def _course_matches_batch(course, student_batch):
	"""Reject a course explicitly labelled for another Form.

	Generic courses without a Form number remain available because some schools
	use names such as 'Religious Studies' across several Forms.
	"""
	batch_level = _form_level(student_batch)
	if batch_level is None:
		return True
	labels = [course]
	course_fields = _meta_fields("Course")
	for fieldname in ("course_name", "course_title", "title"):
		if fieldname in course_fields:
			labels.append(frappe.db.get_value("Course", course, fieldname))
	levels = {_form_level(label) for label in labels if _form_level(label) is not None}
	return not levels or batch_level in levels


def _group_courses(group):
	courses = []
	if group.get("course"):
		courses.append(group.course)
	if not courses and group.get("program") and frappe.db.exists("DocType", "Program Course"):
		pc_fields = _meta_fields("Program Course")
		if "course" in pc_fields:
			courses.extend(frappe.get_all("Program Course", filters={"parent": group.program}, pluck="course", limit_page_length=0))
	return sorted(
		course for course in set(filter(None, courses))
		if _course_matches_batch(course, group.get("student_batch"))
	)


class SchoolTimetableGenerator(Document):
	def validate(self):
		_term(self)
		if self.student_batch:
			batch_program = frappe.db.get_value("Student Batch Name", self.student_batch, "custom_program")
			if batch_program and batch_program != self.program:
				frappe.throw(_("Student Batch {0} belongs to Program {1}, not {2}.").format(
					self.student_batch, batch_program, self.program
				))
		seen = set()
		for row in self.courses:
			key = (row.student_group, row.course)
			if key in seen:
				frappe.throw(_("Student Group {0} and Course {1} are listed more than once.").format(*key))
			seen.add(key)
			if cint(row.periods_per_week) <= 0:
				frappe.throw(_("Periods Per Week must be greater than zero in row {0}.").format(row.idx))
		option_frequencies = defaultdict(set)
		for row in self.courses:
			if row.option_block:
				option_frequencies[(row.student_batch, row.option_block)].add(cint(row.periods_per_week))
		for (batch, block), frequencies in option_frequencies.items():
			if len(frequencies) > 1:
				frappe.throw(_("Every {0} class in batch {1} must use the same Periods Per Week value.").format(block, batch))

	@frappe.whitelist()
	def load_courses(self):
		self.check_permission("write")
		fields, filters = _group_filters(self)
		batch_field = _first_field(fields, "student_batch_name", "student_batch", "batch")
		query_fields = ["name"] + [name for name in ("course", "program") if name in fields]
		if batch_field:
			query_fields.append(f"{batch_field} as student_batch")
		groups = frappe.get_all("Student Group", filters=filters, fields=query_fields, order_by="name asc", limit_page_length=0)
		if not groups:
			frappe.throw(_("No active Student Groups match this Academic Year and Student Batch."))

		term = _term(self)
		schedule_fields = _meta_fields("Course Schedule")
		existing = frappe.get_all(
			"Course Schedule",
			filters={"student_group": ["in", [row.name for row in groups]], "schedule_date": ["between", [term.start_date, term.end_date]], "docstatus": ["<", 2]},
			fields=[name for name in ("student_group", "course", "instructor", "room") if name in schedule_fields],
			order_by="schedule_date desc", limit_page_length=0,
		)
		defaults = {}
		for row in existing:
			key = (row.get("student_group"), row.get("course"))
			if key not in defaults:
				defaults[key] = row

		previous = {(r.student_group, r.course): r.as_dict() for r in self.courses}
		self.set("courses", [])
		for group in groups:
			for course in _group_courses(group):
				current = previous.get((group.name, course)) or defaults.get((group.name, course), {})
				self.append("courses", {
					"student_group": group.name,
					"student_batch": group.get("student_batch"),
					"option_block": _option_block(group.name),
					"course": course,
					"instructor": current.get("instructor"),
					"room": current.get("room"),
					"periods_per_week": current.get("periods_per_week", 3),
					"max_per_day": current.get("max_per_day", 1),
				})
		if not self.courses:
			frappe.throw(_("The matching groups do not expose courses. Add course-based Student Groups or courses to their Program, then reload."))
		self.save()
		return {"loaded": len(self.courses)}

	@frappe.whitelist()
	def print_timetable(self, week_start=None, student_group=None, instructor=None):
		from high_school.high_school.timetable_printing import printable
		return printable(self.name, week_start, student_group, instructor)

	@frappe.whitelist()
	def preview_schedules(self):
		from high_school.high_school.timetable_operations import preview
		return preview(self.name)

	@frappe.whitelist()
	def apply_schedules(self, token=None):
		from high_school.high_school.timetable_operations import apply
		return apply(self.name, token)

	@frappe.whitelist()
	def generate_schedules(self):
		frappe.throw(_("Use Preview Schedule Changes, then Apply. Direct generation is disabled to protect existing timetables."))


@frappe.whitelist()
def generate_schedules(**kwargs):
	"""Retire the old write endpoint without saving client-supplied documents."""
	frappe.throw(_("Use Preview Schedule Changes, then Apply in School Timetable Generator. Refresh your browser after upgrading to v0.0.29."))
