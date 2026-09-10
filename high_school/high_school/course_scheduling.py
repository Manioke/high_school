from datetime import time, timedelta

import frappe
from frappe import _
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
    @frappe.whitelist()
    def schedule_course(self, days):
        apply_school_period(self)
        return super().schedule_course(days)


def normalise_course_schedule_times(doc, method=None):
    if doc.get("from_time") is not None and doc.get("to_time") is not None:
        validate_time_range(doc.from_time, doc.to_time)
        doc.from_time = normalise_time(doc.from_time)
        doc.to_time = normalise_time(doc.to_time)
