import frappe
from frappe import _
from frappe.model.document import Document


class StudentPerformanceSummary(Document):
	def validate(self):
		duplicate = frappe.db.get_value(
			"Student Performance Summary",
			{
				"performance_period": self.performance_period,
				"student": self.student,
				"docstatus": ["<", 2],
				"name": ["!=", self.name],
			},
		)
		if duplicate:
			frappe.throw(
				_("Student {0} already has a performance summary for this period: {1}").format(
					self.student, duplicate
				)
			)

	def before_submit(self):
		if self.status != "Complete":
			frappe.throw(_("An incomplete performance summary cannot be submitted."))
