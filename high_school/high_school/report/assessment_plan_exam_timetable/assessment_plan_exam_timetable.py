from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, cint, format_date, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_validate_filters(filters)
	rows = _get_plans(filters)
	from_date, to_date = _resolve_date_window(filters, rows)
	rows = _within_window(rows, from_date, to_date)

	if filters.display_by == "Student Group":
		columns = _student_group_columns()
		data = _student_group_rows(rows)
	else:
		columns = _course_columns()
		data = _course_rows(rows)

	message = _period_message(from_date, to_date, len(rows))
	return columns, data, message


def _validate_filters(filters):
	for fieldname in ("academic_year", "assessment_group"):
		if not filters.get(fieldname):
			frappe.throw(_("{0} is required.").format(fieldname.replace("_", " ").title()))
	if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))
	if filters.display_by not in {None, "", "Course", "Student Group"}:
		frappe.throw(_("Display By must be Course or Student Group."))


def _get_plans(filters):
	docstatus = ["<", 2] if cint(filters.get("include_draft")) else 1
	return frappe.get_list(
		"Assessment Plan",
		filters={
			"academic_year": filters.academic_year,
			"assessment_group": filters.assessment_group,
			"docstatus": docstatus,
			"schedule_date": ["is", "set"],
		},
		fields=[
			"name",
			"schedule_date",
			"from_time",
			"to_time",
			"course",
			"student_group",
			"room",
			"instructor",
			"docstatus",
		],
		order_by="schedule_date asc, from_time asc, to_time asc, course asc, student_group asc",
	)


def _resolve_date_window(filters, rows):
	from_date = getdate(filters.from_date) if filters.from_date else None
	to_date = getdate(filters.to_date) if filters.to_date else None
	if from_date and not to_date:
		to_date = add_days(from_date, 13)
	elif to_date and not from_date:
		from_date = add_days(to_date, -13)
	elif not from_date and not to_date and rows:
		from_date = getdate(rows[0].schedule_date)
		to_date = getdate(rows[-1].schedule_date)
	return from_date, to_date


def _within_window(rows, from_date, to_date):
	if not from_date or not to_date:
		return rows
	return [row for row in rows if from_date <= getdate(row.schedule_date) <= to_date]


def _day_name(value):
	return getdate(value).strftime("%A")


def _time_value(value):
	return str(value or "")


def _period_message(from_date, to_date, plan_count):
	if not from_date or not to_date:
		return _("No scheduled Assessment Plans were found for the selected examination.")
	return _("Timetable period: {0} to {1}. {2} group-specific Assessment Plan(s) included.").format(
		format_date(from_date), format_date(to_date), plan_count
	)


def _base_columns():
	return [
		{"fieldname": "schedule_date", "label": _("Date"), "fieldtype": "Date", "width": 105},
		{"fieldname": "day", "label": _("Day"), "fieldtype": "Data", "width": 95},
		{"fieldname": "from_time", "label": _("Start"), "fieldtype": "Time", "width": 90},
		{"fieldname": "to_time", "label": _("End"), "fieldtype": "Time", "width": 90},
	]


def _course_columns():
	return _base_columns() + [
		{
			"fieldname": "course",
			"label": _("Course / Examination"),
			"fieldtype": "Link",
			"options": "Course",
			"width": 210,
		},
		{"fieldname": "student_groups", "label": _("Student Groups"), "fieldtype": "Data", "width": 240},
		{"fieldname": "rooms", "label": _("Room(s)"), "fieldtype": "Data", "width": 140},
		{"fieldname": "plan_count", "label": _("Plans"), "fieldtype": "Int", "width": 65},
	]


def _student_group_columns():
	return _base_columns() + [
		{
			"fieldname": "student_group",
			"label": _("Student Group"),
			"fieldtype": "Link",
			"options": "Student Group",
			"width": 170,
		},
		{
			"fieldname": "course",
			"label": _("Course / Examination"),
			"fieldtype": "Link",
			"options": "Course",
			"width": 210,
		},
		{"fieldname": "room", "label": _("Room"), "fieldtype": "Link", "options": "Room", "width": 120},
		{
			"fieldname": "instructor",
			"label": _("Course Instructor"),
			"fieldtype": "Link",
			"options": "Instructor",
			"width": 150,
		},
		{
			"fieldname": "assessment_plan",
			"label": _("Assessment Plan"),
			"fieldtype": "Link",
			"options": "Assessment Plan",
			"width": 170,
		},
	]


def _course_rows(rows):
	grouped = defaultdict(list)
	for row in rows:
		key = (
			row.schedule_date,
			_time_value(row.from_time),
			_time_value(row.to_time),
			row.course,
		)
		grouped[key].append(row)

	data = []
	for key in sorted(grouped, key=lambda value: (value[0], value[1], value[2], value[3] or "")):
		plans = grouped[key]
		data.append(
			{
				"schedule_date": key[0],
				"day": _day_name(key[0]),
				"from_time": key[1],
				"to_time": key[2],
				"course": key[3],
				"student_groups": ", ".join(sorted({row.student_group for row in plans if row.student_group})),
				"rooms": ", ".join(sorted({row.room for row in plans if row.room})),
				"plan_count": len(plans),
			}
		)
	return data


def _student_group_rows(rows):
	return [
		{
			"schedule_date": row.schedule_date,
			"day": _day_name(row.schedule_date),
			"from_time": row.from_time,
			"to_time": row.to_time,
			"student_group": row.student_group,
			"course": row.course,
			"room": row.room,
			"instructor": row.instructor,
			"assessment_plan": row.name,
		}
		for row in rows
	]
