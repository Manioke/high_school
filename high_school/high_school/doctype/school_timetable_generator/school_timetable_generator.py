from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, now_datetime

from high_school.high_school.course_scheduling import normalise_time


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


def _school_periods():
	periods = frappe.get_all(
		"School Period", fields=["name", "period_name", "from_time", "to_time"], order_by="from_time asc", limit_page_length=0
	)
	periods = [row for row in periods if row.from_time is not None and row.to_time is not None]
	if not periods:
		frappe.throw(_("Create at least one School Period with From Time and To Time before generating a timetable."))
	return periods


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
			limit_page_length=0,
		)
		defaults = {}
		for row in existing:
			key = (row.get("student_group"), row.get("course"))
			if key not in defaults:
				defaults[key] = row

		self.set("courses", [])
		for group in groups:
			for course in _group_courses(group):
				current = defaults.get((group.name, course), {})
				self.append("courses", {
					"student_group": group.name,
					"student_batch": group.get("student_batch"),
					"option_block": _option_block(group.name),
					"course": course,
					"instructor": current.get("instructor"),
					"room": current.get("room"),
					"periods_per_week": 3,
				})
		if not self.courses:
			frappe.throw(_("The matching groups do not expose courses. Add course-based Student Groups or courses to their Program, then reload."))
		self.save()
		return {"loaded": len(self.courses)}

	@frappe.whitelist()
	def generate_schedules(self):
		self.check_permission("write")
		self.validate()
		if not self.courses:
			frappe.throw(_("Load or add timetable course rows first."))
		missing_instructors = [str(row.idx) for row in self.courses if not row.instructor]
		if missing_instructors:
			frappe.throw(_("Select an Instructor in timetable row(s): {0}.").format(", ".join(missing_instructors)))
		missing_rooms = [str(row.idx) for row in self.courses if not row.room]
		if _room_required() and missing_rooms:
			frappe.throw(_("Select a Room in timetable row(s): {0}. Rooms are mandatory in School MIS Settings.").format(", ".join(missing_rooms)))

		term = _term(self)
		periods = _school_periods()
		start, end = getdate(term.start_date), getdate(term.end_date)
		dates = []
		current = start
		while current <= end:
			if current.weekday() < 5:
				dates.append(current)
			current += timedelta(days=1)
		weeks = defaultdict(list)
		for value in dates:
			monday = value - timedelta(days=value.weekday())
			weeks[monday].append(value)

		cs_fields = _meta_fields("Course Schedule")
		query_fields = [name for name in ("name", "student_group", "course", "instructor", "room", "schedule_date", "from_time", "to_time") if name in cs_fields]
		existing = frappe.get_all(
			"Course Schedule",
			filters={"schedule_date": ["between", [start, end]], "docstatus": ["<", 2]},
			fields=query_fields,
			limit_page_length=0,
		)

		def overlaps(a_start, a_end, b_start, b_end):
			return a_start < b_end and a_end > b_start

		group_info = {
			row.student_group: frappe._dict(
				student_batch=row.student_batch,
				option_block=row.option_block or _option_block(row.student_group),
			)
			for row in self.courses
		}
		missing_groups = {item.get("student_group") for item in existing if item.get("student_group")} - set(group_info)
		if missing_groups:
			group_fields = _meta_fields("Student Group")
			batch_field = _first_field(group_fields, "student_batch_name", "student_batch", "batch")
			fields = ["name"] + ([f"{batch_field} as student_batch"] if batch_field else [])
			for group in frappe.get_all("Student Group", filters={"name": ["in", list(missing_groups)]}, fields=fields, limit_page_length=0):
				group_info[group.name] = frappe._dict(student_batch=group.get("student_batch"), option_block=_option_block(group.name))

		option_slots = {}
		for item in existing:
			info = group_info.get(item.get("student_group"))
			if not info or not info.option_block or not info.student_batch:
				continue
			option_slots[(info.student_batch, getdate(item.schedule_date), normalise_time(item.from_time), normalise_time(item.to_time))] = info.option_block

		def blocked(row, date, period):
			p_start, p_end = normalise_time(period.from_time), normalise_time(period.to_time)
			for item in existing:
				if getdate(item.schedule_date) != date:
					continue
				if not overlaps(p_start, p_end, normalise_time(item.from_time), normalise_time(item.to_time)):
					continue
				if item.get("student_group") == row.student_group or item.get("instructor") == row.instructor:
					return True
				if row.room and item.get("room") == row.room:
					return True
			return False

		planned = []
		unscheduled = []
		bundles = defaultdict(list)
		for row in self.courses:
			if row.option_block and row.student_batch:
				key = ("option", row.student_batch, row.option_block)
			else:
				key = ("course", row.student_group, row.course)
			bundles[key].append(row)
		ordered_bundles = sorted(
			bundles.items(),
			key=lambda item: (-cint(item[1][0].periods_per_week), str(item[0])),
		)
		for monday, week_dates in sorted(weeks.items()):
			for bundle_key, bundle_rows in ordered_bundles:
				required = cint(bundle_rows[0].periods_per_week)
				instructors = [row.instructor for row in bundle_rows if row.instructor]
				rooms = [row.room for row in bundle_rows if row.room]
				if len(instructors) != len(set(instructors)):
					frappe.throw(_("{0} uses the same Instructor for simultaneous option classes. Assign a different Instructor to each row.").format(bundle_key[-1]))
				if _room_required() and len(rooms) != len(set(rooms)):
					frappe.throw(_("{0} uses the same Room for simultaneous option classes. Assign a different Room to each row.").format(bundle_key[-1]))
				placed_days = set()
				row_slots = []
				for row in bundle_rows:
					slots = {
						(getdate(item.schedule_date), normalise_time(item.from_time), normalise_time(item.to_time))
						for item in existing
						if getdate(item.schedule_date) in week_dates
						and item.get("student_group") == row.student_group
						and item.get("course") == row.course
						and item.get("instructor") == row.instructor
					}
					row_slots.append(slots)
				common_slots = set.intersection(*row_slots) if row_slots else set()
				placed = min(len(common_slots), required)
				placed_days.update(slot[0].weekday() for slot in common_slots)
				candidates = [(date, period) for date in week_dates for period in periods]
				candidates.sort(key=lambda item: (item[0].weekday() in placed_days, item[0].weekday(), normalise_time(item[1].from_time)))
				for date, period in candidates:
					if placed >= required:
						break
					if date.weekday() in placed_days and required <= len(week_dates):
						continue
					p_start, p_end = normalise_time(period.from_time), normalise_time(period.to_time)
					if bundle_key[0] == "option":
						occupied = option_slots.get((bundle_key[1], date, p_start, p_end))
						if occupied and occupied != bundle_key[2]:
							continue
					if any(blocked(row, date, period) for row in bundle_rows):
						continue
					for row in bundle_rows:
						values = {
							"student_group": row.student_group, "course": row.course, "instructor": row.instructor,
							"room": row.room, "schedule_date": date, "from_time": p_start,
							"to_time": p_end, "period": period.name,
						}
						planned.append(values)
						existing.append(frappe._dict(values))
					if bundle_key[0] == "option":
						option_slots[(bundle_key[1], date, p_start, p_end)] = bundle_key[2]
					placed_days.add(date.weekday())
					placed += 1
				if placed < required:
					label = _("{0} option block for {1}").format(bundle_key[2], bundle_key[1]) if bundle_key[0] == "option" else _("{0} / {1}").format(bundle_rows[0].student_group, bundle_rows[0].course)
					unscheduled.append(_("Week of {0}: {1} ({2} of {3} placed)").format(monday, label, placed, required))

		if unscheduled:
			frappe.throw(
				_("The timetable has unresolved conflicts. Nothing was created.<br>{0}").format("<br>".join(unscheduled[:50])),
				title=_("Unscheduled Timetable Courses"),
			)

		created, skipped = [], []
		for values in planned:
			duplicate = frappe.db.exists("Course Schedule", {
				"student_group": values["student_group"], "course": values["course"],
				"schedule_date": values["schedule_date"], "from_time": values["from_time"], "to_time": values["to_time"],
				"docstatus": ["<", 2],
			})
			if duplicate:
				skipped.append(duplicate)
				continue
			group = frappe.db.get_value("Student Group", values["student_group"], ["program"], as_dict=True) or {}
			doc = frappe.new_doc("Course Schedule")
			payload = {key: values[key] for key in ("student_group", "course", "instructor", "room", "schedule_date", "from_time", "to_time") if key in cs_fields and values.get(key)}
			if "program" in cs_fields and group.get("program"):
				payload["program"] = group.program
			if "academic_year" in cs_fields:
				payload["academic_year"] = self.academic_year
			if "custom_period" in cs_fields:
				payload["custom_period"] = values["period"]
			if "custom_school_term" in cs_fields:
				payload["custom_school_term"] = self.school_term
			if "custom_timetable_generator" in cs_fields:
				payload["custom_timetable_generator"] = self.name
			doc.update(payload)
			doc.insert()
			created.append(doc.name)

		self.generated_schedule_count = len(created)
		self.last_generated_on = now_datetime()
		self.save()
		return {"created": created, "skipped": skipped, "weeks": len(weeks)}
