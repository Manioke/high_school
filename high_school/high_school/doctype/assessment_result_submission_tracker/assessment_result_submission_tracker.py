import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, nowdate


class AssessmentResultSubmissionTracker(Document):
	def before_validate(self):
		self._load_linked_values()
		self._populate_candidates_once()

	def validate(self):
		self._validate_unique_plan()
		self._validate_candidate_exceptions()
		self.update_coverage()

	def _load_linked_values(self):
		if not self.assessment_plan or not frappe.db.exists("Assessment Plan", self.assessment_plan):
			return
		plan = frappe.get_doc("Assessment Plan", self.assessment_plan)
		for fieldname in ("academic_year", "assessment_group", "course", "student_group"):
			self.set(fieldname, plan.get(fieldname))
		self.assessment_date = plan.get("schedule_date")

		if self.exam_paper_requirement:
			requirement = frappe.get_doc("Exam Paper Requirement", self.exam_paper_requirement)
			self.examination_cycle = requirement.examination_cycle
			self.school_term = requirement.school_term
			self.hod_user = requirement.hod_user
			cycle = frappe.get_doc("School Examination Cycle", requirement.examination_cycle)
			self.assessment_type = cycle.assessment_type or "Examination"
			from high_school.high_school.result_submission import calculate_result_due_date

			self.result_due_date = calculate_result_due_date(cycle, plan)

		from high_school.high_school.result_submission import resolve_plan_responsibility

		responsibility = resolve_plan_responsibility(plan)
		self.instructor = responsibility.get("instructor")
		self.responsible_user = responsibility.get("responsible_user")
		self.instructor_mapping_issue = responsibility.get("issue")

	def _populate_candidates_once(self):
		if self.candidates or not self.student_group:
			return
		students = frappe.get_all(
			"Student Group Student",
			filters={"parent": self.student_group, "active": 1},
			fields=["student", "student_name"],
			order_by="idx asc",
		)
		for student in students:
			self.append(
				"candidates",
				{
					"student": student.student,
					"student_name": student.student_name,
					"result_status": "Pending",
				},
			)

	def _validate_unique_plan(self):
		duplicate = frappe.db.get_value(
			"Assessment Result Submission Tracker",
			{
				"assessment_plan": self.assessment_plan,
				"name": ["!=", self.name or ""],
			},
		)
		if duplicate:
			frappe.throw(_("Assessment Plan {0} is already tracked by {1}.").format(self.assessment_plan, duplicate))

	def _validate_candidate_exceptions(self):
		seen = set()
		for row in self.candidates:
			if row.student in seen:
				frappe.throw(_("Student {0} is listed more than once.").format(row.student))
			seen.add(row.student)
			if row.non_participation and not (row.reason or "").strip():
				frappe.throw(
					_("Enter a reason for {0}, who is marked {1}.").format(
						row.student_name or row.student, row.non_participation
					)
				)

	def update_coverage(self):
		students = [row.student for row in self.candidates]
		results = []
		if self.assessment_plan and students:
			results = frappe.get_all(
				"Assessment Result",
				filters={
					"assessment_plan": self.assessment_plan,
					"student": ["in", students],
					"docstatus": ["<", 2],
				},
				fields=["name", "student", "docstatus", "modified"],
				order_by="docstatus desc, modified desc",
			)

		result_by_student = {}
		for result in results:
			current = result_by_student.get(result.student)
			if not current or result.docstatus > current.docstatus:
				result_by_student[result.student] = result

		draft = submitted = non_participation = missing = 0
		for row in self.candidates:
			result = result_by_student.get(row.student)
			row.assessment_result = result.name if result else None
			if result and result.docstatus == 1:
				row.result_status = "Submitted"
				submitted += 1
			elif row.non_participation:
				row.result_status = row.non_participation
				non_participation += 1
			elif result:
				row.result_status = "Draft"
				draft += 1
				missing += 1
			else:
				row.result_status = "Pending"
				missing += 1

		expected = len(self.candidates)
		resolved = submitted + non_participation
		self.expected_student_count = expected
		self.draft_result_count = draft
		self.submitted_result_count = submitted
		self.non_participation_count = non_participation
		self.missing_result_count = missing
		self.completion_percentage = flt(resolved / expected * 100, 2) if expected else 100

		plan_status = frappe.db.get_value("Assessment Plan", self.assessment_plan, "docstatus")
		if plan_status == 2 or plan_status is None:
			self.status = "Plan Cancelled"
		elif plan_status == 0:
			self.status = "Awaiting Plan Submission"
		elif self.instructor_mapping_issue:
			self.status = "Instructor Mapping Error"
		elif not expected or not missing:
			self.status = "Results Complete"
		elif self.result_due_date and getdate(self.result_due_date) < getdate(nowdate()):
			self.status = "Overdue"
		elif self.assessment_date and getdate(self.assessment_date) > getdate(nowdate()):
			self.status = "Awaiting Assessment"
		elif draft or submitted:
			self.status = "Marking In Progress"
		else:
			self.status = "Awaiting Results"

		if self.status == "Results Complete" and not self.completed_on:
			self.completed_on = now_datetime()
		elif self.status != "Results Complete":
			self.completed_on = None

	@frappe.whitelist()
	def refresh_coverage(self):
		self.check_permission("write")
		self.save(ignore_permissions=True)
		return {
			"status": self.status,
			"expected": self.expected_student_count,
			"submitted": self.submitted_result_count,
			"non_participation": self.non_participation_count,
			"missing": self.missing_result_count,
		}
