# Copyright (c) 2026, Sione Hikaione Fonua Kata and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from high_school.high_school.course_scheduling import normalise_time, validate_time_range


class SchoolPeriod(Document):
	def validate(self):
		if self.from_time is None or self.to_time is None:
			frappe.throw(_("Enter both From Time and To Time."))
		validate_time_range(self.from_time, self.to_time)
		self.from_time = normalise_time(self.from_time)
		self.to_time = normalise_time(self.to_time)
