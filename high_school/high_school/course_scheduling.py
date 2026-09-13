from datetime import time, timedelta

import frappe
from frappe import _
from frappe.utils import cint
from education.education.doctype.course_scheduling_tool.course_scheduling_tool import (
    CourseSchedulingTool as EducationCourseSchedulingTool,
)


def _seconds(value):
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    if isinstance(value, time):
        return value.hour * 3600 + value.minute * 60 + value.second
    parts = str(value or "").split(":")
    if len(parts) < 2:
        frappe.throw(_("Enter a valid School Period time."))
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2] if len(parts) > 2 else 0))


def normalise_time(value):
    seconds = _seconds(value)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def validate_time_range(from_time, to_time):
    if _seconds(from_time) >= _seconds(to_time):
        frappe.throw(_("From Time must be earlier than To Time."))


def apply_school_period(doc):
    if not doc.get("custom_period"):
        frappe.throw(_("Select a School Period before scheduling the course."))
    period = frappe.db.get_value(
        "School Period", doc.custom_period, ["from_time", "to_time"], as_dict=True
    )
    if not period or period.from_time is None or period.to_time is None:
        frappe.throw(_("School Period {0} must have both From Time and To Time.").format(doc.custom_period))
    validate_time_range(period.from_time, period.to_time)
    doc.from_time = normalise_time(period.from_time)
    doc.to_time = normalise_time(period.to_time)


class HighSchoolCourseSchedulingTool(EducationCourseSchedulingTool):
	def validate_mandatory(self, days):
		if cint(frappe.db.get_single_value("School MIS Settings", "require_rooms_for_timetable")):
			return super().validate_mandatory(days)
		if not days:
			frappe.throw(_("Please select at least one day to schedule the course."))
		for fieldname in ("course", "instructor", "from_time", "to_time", "course_start_date", "course_end_date"):
			if not self.get(fieldname):
				frappe.throw(_("{0} is mandatory").format(self.meta.get_label(fieldname)))

	@frappe.whitelist()
	def schedule_course(self, days):
		apply_school_period(self)
		return super().schedule_course(days)


def normalise_course_schedule_times(doc, method=None):
	require_room = cint(frappe.db.get_single_value("School MIS Settings", "require_rooms_for_timetable"))
	if require_room and not doc.get("room"):
		frappe.throw(_("Room is mandatory because Require Rooms for Timetables is enabled in School MIS Settings."))
	if not require_room and not doc.get("room"):
		# Education v16 marks Room mandatory in the standard DocType. This
		# setting deliberately relaxes only that requirement; all other required
		# scheduling fields are validated by the standard controller.
		doc.flags.ignore_mandatory = True
	if doc.get("custom_period"):
		period = frappe.db.get_value("School Period", doc.custom_period, ["from_time", "to_time"], as_dict=True)
		if not period:
			frappe.throw(_("School Period {0} does not exist.").format(doc.custom_period))
		doc.from_time = period.from_time
		doc.to_time = period.to_time
	if doc.get("from_time") is not None and doc.get("to_time") is not None:
		validate_time_range(doc.from_time, doc.to_time)
		doc.from_time = normalise_time(doc.from_time)
		doc.to_time = normalise_time(doc.to_time)
