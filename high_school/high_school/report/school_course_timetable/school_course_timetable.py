from collections import defaultdict
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import format_date, getdate


def _meta_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.academic_year or not filters.program or not filters.school_term:
		frappe.throw(_("Academic Year, Program, and School Term are required."))
	term = frappe.db.get_value("School Term", filters.school_term, ["academic_year", "start_date", "end_date"], as_dict=True)
	if not term or term.academic_year != filters.academic_year:
		frappe.throw(_("The selected School Term does not belong to the selected Academic Year."))
	anchor = getdate(filters.week_start or term.start_date)
	monday = anchor - timedelta(days=anchor.weekday())
	friday = monday + timedelta(days=4)

	group_fields = _meta_fields("Student Group")
	batch_field = next((name for name in ("student_batch_name", "student_batch", "batch") if name in group_fields), None)
	group_filters = {"academic_year": filters.academic_year}
	if filters.program and "program" in group_fields:
		group_filters["program"] = filters.program
	if filters.student_group:
		group_filters["name"] = filters.student_group
	if filters.student_batch and batch_field:
		group_filters[batch_field] = filters.student_batch
	groups = frappe.get_all("Student Group", filters=group_filters, pluck="name", limit_page_length=0)
	if not groups:
		return _columns(monday), [], _("No matching Student Groups were found.")

	cs_fields = _meta_fields("Course Schedule")
	query_filters = {
		"student_group": ["in", groups],
		"schedule_date": ["between", [monday, friday]],
		"docstatus": ["<", 2],
	}
	if filters.instructor:
		query_filters["instructor"] = filters.instructor
	if "custom_school_term" in cs_fields:
		query_filters["custom_school_term"] = filters.school_term
	rows = frappe.get_all(
		"Course Schedule",
		filters=query_filters,
		fields=[name for name in ("name", "schedule_date", "from_time", "to_time", "custom_period", "course", "student_group", "instructor", "room") if name in cs_fields],
		order_by="schedule_date asc, from_time asc, course asc",
		limit_page_length=0,
	)
	periods = frappe.get_all("School Period", fields=["name", "period_name", "from_time", "to_time"], order_by="from_time asc", limit_page_length=0)
	by_slot = defaultdict(list)
	for row in rows:
		period = row.get("custom_period") or next((p.name for p in periods if str(p.from_time) == str(row.from_time) and str(p.to_time) == str(row.to_time)), None)
		if period:
			by_slot[(period, getdate(row.schedule_date).weekday())].append(row)

	data = []
	for period in periods:
		item = {"period": period.period_name or period.name, "time": f"{period.from_time} - {period.to_time}"}
		for day in range(5):
			values = []
			for row in by_slot.get((period.name, day), []):
				label = f"{row.course} — {row.student_group}"
				if row.get("instructor"):
					label += f" — {row.instructor}"
				if row.get("room"):
					label += f" ({row.room})"
				values.append(label)
			item[f"day_{day}"] = "\n".join(values)
		data.append(item)
	return _columns(monday), data, _("Printable teaching timetable for {0} to {1}.").format(format_date(monday), format_date(friday))


def _columns(monday):
	columns = [
		{"fieldname": "period", "label": _("School Period"), "fieldtype": "Data", "width": 130},
		{"fieldname": "time", "label": _("Time"), "fieldtype": "Data", "width": 125},
	]
	for day in range(5):
		date = monday + timedelta(days=day)
		columns.append({"fieldname": f"day_{day}", "label": f"{date.strftime('%A')} {date.strftime('%d %b')}", "fieldtype": "Data", "width": 240})
	return columns
