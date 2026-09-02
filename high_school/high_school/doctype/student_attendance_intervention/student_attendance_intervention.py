import frappe

from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class StudentAttendanceIntervention(Document):
    def validate(self):
        if self.status in {"Resolved", "Dismissed"} and not self.resolution_notes:
            frappe.throw(
                _("Resolution Notes are required before closing this follow-up.")
            )
        if self.status in {"Resolved", "Dismissed"} and not self.resolved_on:
            self.resolved_on = now_datetime()
            self.resolved_attendance_records = self.attendance_records or 0
        elif self.status not in {"Resolved", "Dismissed"}:
            self.resolved_on = None
            self.resolved_attendance_records = 0
        if self.status == "Meeting Scheduled" and not self.meeting_date:
            frappe.throw(
                _("Meeting Date and Time is required when a meeting is scheduled.")
            )
