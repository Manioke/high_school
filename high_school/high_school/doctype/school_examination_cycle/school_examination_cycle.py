import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class SchoolExaminationCycle(Document):
	def validate(self):
		self._validate_school_term()
		self._validate_dates()
		self._validate_unique_rows()
		self._validate_result_deadline()
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
			("hod_assignments", "department", _("Department")),
		):
			seen = set()
			for row in self.get(fieldname):
				value = row.get(key)
				if value in seen:
					frappe.throw(_("{0} {1} is listed more than once.").format(label, value))
				seen.add(value)

		selected_batches = {row.student_batch for row in self.student_batches}
		seen_courses = set()
		for row in self.courses:
			if row.student_batch and row.student_batch not in selected_batches:
				frappe.throw(
					_("Course {0} is assigned to Student Batch {1}, which is not included in this cycle.").format(
						row.course, row.student_batch
					)
				)
			key = (row.student_batch or "", row.course)
			if key in seen_courses:
				frappe.throw(
					_("Course {0} is listed more than once for Student Batch {1}.").format(
						row.course, row.student_batch or _("Unspecified")
					)
				)
			seen_courses.add(key)

	def _validate_result_deadline(self):
		if self.result_deadline_basis == "Fixed Date":
			if not self.fixed_result_deadline:
				frappe.throw(_("Fixed Result Submission Deadline is required when Result Deadline Basis is Fixed Date."))
			if getdate(self.fixed_result_deadline) < getdate(self.exam_start_date):
				frappe.throw(_("The result submission deadline cannot be before the assessment period begins."))
		elif (self.result_turnaround_days or 0) < 0:
			frappe.throw(_("Result Turnaround Days cannot be negative."))

	@frappe.whitelist()
	def generate_requirements(self):
		self.check_permission("write")
		from high_school.high_school.exam_preparation import generate_exam_paper_requirements

		return generate_exam_paper_requirements(self)

	@frappe.whitelist()
	def generate_result_trackers(self):
		self.check_permission("write")
		from high_school.high_school.result_submission import generate_trackers_for_cycle

		return generate_trackers_for_cycle(self.name)
