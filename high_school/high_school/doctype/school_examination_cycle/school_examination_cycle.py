import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class SchoolExaminationCycle(Document):
	def validate(self):
		self._validate_school_term()
		self._validate_dates()
		self._validate_unique_rows()
		if self.course_selection_policy == "Selected Courses" and not self.courses:
			frappe.throw(_("Add at least one Course when Course Selection Policy is Selected Courses."))

	def _validate_school_term(self):
		term_year = frappe.db.get_value("School Term", self.school_term, "academic_year")
		if term_year and term_year != self.academic_year:
			frappe.throw(
				_("School Term {0} belongs to Academic Year {1}, not {2}.").format(
					self.school_term, term_year, self.academic_year
				)
			)

	def _validate_dates(self):
		if getdate(self.exam_end_date) < getdate(self.exam_start_date):
			frappe.throw(_("Examination End Date cannot be before Examination Start Date."))
		ordered = [
			("Teacher Assignment Deadline", self.assignment_deadline),
			("Paper Submission Deadline", self.paper_submission_deadline),
			("HOD Review Deadline", self.hod_review_deadline),
			("Final Approval Deadline", self.admin_approval_deadline),
			("Examination Start Date", self.exam_start_date),
		]
		for (previous_label, previous), (current_label, current) in zip(ordered, ordered[1:]):
			if previous and current and getdate(current) < getdate(previous):
				frappe.throw(_("{0} cannot be before {1}.").format(current_label, previous_label))

	def _validate_unique_rows(self):
		for fieldname, key, label in (
			("student_batches", "student_batch", _("Student Batch")),
			("courses", "course", _("Course")),
			("hod_assignments", "department", _("Department")),
		):
			seen = set()
			for row in self.get(fieldname):
				value = row.get(key)
				if value in seen:
					frappe.throw(_("{0} {1} is listed more than once.").format(label, value))
				seen.add(value)

	@frappe.whitelist()
	def generate_requirements(self):
		self.check_permission("write")
		from high_school.high_school.exam_preparation import generate_exam_paper_requirements

		return generate_exam_paper_requirements(self)
