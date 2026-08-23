import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SchoolPerformancePeriod(Document):
	def validate(self):
		self._validate_school_term()
		self._validate_main_student_group()
		self._validate_settings()
		self._validate_components()
		self._validate_submitted_summary_lock()

	def _validate_school_term(self):
		term_year = frappe.db.get_value("School Term", self.school_term, "academic_year")
		if term_year and term_year != self.academic_year:
			frappe.throw(
				_("School Term {0} belongs to Academic Year {1}, not {2}.").format(
					self.school_term, term_year, self.academic_year
				)
			)

	def _validate_components(self):
		if not self.components:
			frappe.throw(_("Add at least one assessment component."))

		seen = set()
		for row in self.components:
			if row.assessment_group in seen:
				frappe.throw(_("Assessment Group {0} is listed more than once.").format(row.assessment_group))
			seen.add(row.assessment_group)
			if flt(row.weight) <= 0:
				frappe.throw(_("Each assessment component must have a weight greater than zero."))

		total = sum(flt(row.weight) for row in self.components)
		if abs(total - 100) > 0.001:
			frappe.throw(_("Assessment component weights must total 100%. Current total: {0}%.").format(total))

	def _validate_main_student_group(self):
		group_year = frappe.db.get_value("Student Group", self.main_student_group, "academic_year")
		if group_year and group_year != self.academic_year:
			frappe.throw(
				_("Main Student Group {0} belongs to Academic Year {1}, not {2}.").format(
					self.main_student_group, group_year, self.academic_year
				)
			)

	def _validate_settings(self):
		if self.minimum_subjects < 1:
			frappe.throw(_("Minimum Subjects Required must be at least 1."))
		if self.rounding_precision < 0 or self.rounding_precision > 4:
			frappe.throw(_("Displayed Decimal Places must be between 0 and 4."))

	def _validate_submitted_summary_lock(self):
		before = self.get_doc_before_save()
		if not before or not frappe.db.exists(
			"Student Performance Summary",
			{"performance_period": self.name, "docstatus": 1},
		):
			return

		fields = [
			"academic_year",
			"school_term",
			"main_student_group",
			"result_status_filter",
			"missing_result_policy",
			"tie_method",
			"minimum_subjects",
			"rounding_precision",
		]
		changed = any(self.get(field) != before.get(field) for field in fields)
		old_components = [(row.assessment_group, flt(row.weight)) for row in before.components]
		new_components = [(row.assessment_group, flt(row.weight)) for row in self.components]
		if changed or old_components != new_components:
			frappe.throw(
				_("Cancel the submitted performance summaries before changing calculation rules for this period.")
			)
