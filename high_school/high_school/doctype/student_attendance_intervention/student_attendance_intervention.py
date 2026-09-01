import frappe

from frappe import _
from frappe.model.document import Document


class StudentAttendanceIntervention(Document):
    def validate(self):
        if self.status in {"Resolved", "Dismissed"} and not self.resolution_notes:
            frappe.throw(
                _("Resolution Notes are required before closing this follow-up.")
            )
        if self.status == "Meeting Scheduled" and not self.meeting_date:
            frappe.throw(
                _("Meeting Date and Time is required when a meeting is scheduled.")
            )

