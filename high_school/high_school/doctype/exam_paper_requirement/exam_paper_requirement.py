import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


MANAGER_ROLES = {"System Manager", "Education Manager"}
TEACHER_EDITABLE_STATUSES = {"Assigned", "In Preparation", "Changes Requested"}
PLAN_STATUSES = {"Approved", "Plans Partially Created", "Complete"}


class ExamPaperRequirement(Document):
	def before_validate(self):
		self._preserve_workflow_status()
		self._set_cycle_values()
		self._set_title()

	def _preserve_workflow_status(self):
		"""Keep ordinary form saves from changing a server-managed workflow status.

		File uploads save the parent form and can send the status that was on the
		client before the previous save completed. All valid status transitions are
		performed by this controller with ``in_workflow_action`` set, or in
		``before_save`` for the automatic draft states.
		"""
		before = self.get_doc_before_save()
		if before and not self.flags.in_workflow_action:
			self.status = before.status

	def validate(self):
		self._validate_unique_requirement()
		self._validate_people()
		self._validate_criteria()
		self._validate_affected_groups()
		self._validate_protected_changes()
		self.update_plan_coverage()

	def _set_cycle_values(self):
		if not self.examination_cycle:
			return
		cycle = frappe.db.get_value(
			"School Examination Cycle",
			self.examination_cycle,
			[
				"academic_year",
				"school_term",
				"assessment_group",
				"assignment_deadline",
				"paper_submission_deadline",
				"hod_review_deadline",
				"admin_approval_deadline",
				"exam_start_date",
				"blueprint_requirement",
				"question_paper_required",
				"marking_scheme_required",
			],
			as_dict=True,
		)
		if not cycle:
			return
		for fieldname, value in cycle.items():
			self.set(fieldname, value)

	def _set_title(self):
		if self.student_batch and self.course:
			self.requirement_title = "{0} - {1}".format(self.student_batch, self.course)

	def _validate_unique_requirement(self):
		filters = {
			"examination_cycle": self.examination_cycle,
			"student_batch": self.student_batch,
			"course": self.course,
			"name": ["!=", self.name or ""],
		}
		if frappe.db.exists("Exam Paper Requirement", filters):
			frappe.throw(
				_("An Exam Paper Requirement already exists for {0} and {1} in this cycle.").format(
					self.student_batch, self.course
				)
			)

	def _validate_people(self):
		collaborators = [row.user for row in self.collaborators]
		if len(collaborators) != len(set(collaborators)):
			frappe.throw(_("A collaborating teacher is listed more than once."))
		if self.lead_teacher_user and self.lead_teacher_user in collaborators:
			frappe.throw(_("The Lead Teacher does not need to be listed again as a collaborator."))

	def _validate_criteria(self):
		seen = set()
		for row in self.assessment_criteria:
			if row.assessment_criteria in seen:
				frappe.throw(_("Assessment Criterion {0} is listed more than once.").format(row.assessment_criteria))
			if flt(row.maximum_score) <= 0:
				frappe.throw(_("Every Assessment Criterion must have a Maximum Score greater than zero."))
			seen.add(row.assessment_criteria)
		self.maximum_score = sum(flt(row.maximum_score) for row in self.assessment_criteria)

	def _validate_affected_groups(self):
		groups = [row.student_group for row in self.affected_student_groups]
		if len(groups) != len(set(groups)):
			frappe.throw(_("An affected Student Group is listed more than once."))
		for group in groups:
			group_year = frappe.db.get_value("Student Group", group, "academic_year")
			if group_year and group_year != self.academic_year:
				frappe.throw(
					_("Student Group {0} belongs to Academic Year {1}, not {2}.").format(
						group, group_year, self.academic_year
					)
				)

	def _validate_protected_changes(self):
		if self.flags.in_workflow_action:
			return
		before = self.get_doc_before_save()
		if not before:
			return
		roles = set(frappe.get_roles())
		is_manager = bool(roles & MANAGER_ROLES)
		is_hod = frappe.session.user == before.hod_user
		teacher_content_fields = {
			"blueprint_file",
			"question_paper_file",
			"marking_scheme_file",
			"duration_minutes",
			"teacher_notes",
		}
		teacher_content_changed = any(
			self._field_changed(before, fieldname) for fieldname in teacher_content_fields
		) or self._criteria_signature() != self._criteria_signature(before)
		if before.status not in (TEACHER_EDITABLE_STATUSES | {"Awaiting Assignment"}) and teacher_content_changed:
			frappe.throw(_("Request changes through the workflow before modifying submitted examination content."))
		assignment_fields = {"department", "hod_user", "lead_teacher_user"}
		manager_fields = {
			"examination_cycle",
			"student_batch",
			"course",
			"examination_date",
			"from_time",
			"to_time",
			"room",
			"grading_scale",
		}
		scope_changed = any(self._field_changed(before, fieldname) for fieldname in manager_fields)
		scope_changed = scope_changed or self._table_signature(
			"affected_student_groups", ("student_group",)
		) != self._table_signature("affected_student_groups", ("student_group",), before)
		if scope_changed and not is_manager:
			frappe.throw(_("Only an Education Manager can change the examination scope or schedule."))
		assignment_changed = any(self._field_changed(before, fieldname) for fieldname in assignment_fields)
		assignment_changed = assignment_changed or self._table_signature(
			"collaborators", ("user",)
		) != self._table_signature("collaborators", ("user",), before)
		if assignment_changed:
			if not (is_manager or is_hod):
				frappe.throw(_("Only the HOD or Education Manager can change paper assignments."))
			if self._field_changed(before, "hod_user") and not is_manager:
				frappe.throw(_("Only an Education Manager can change the HOD."))

		if not is_manager and not is_hod and self.status not in TEACHER_EDITABLE_STATUSES:
			frappe.throw(_("This paper cannot be edited by a teacher while its status is {0}.").format(self.status))

	def before_save(self):
		before = self.get_doc_before_save()
		if self.lead_teacher_user and self.status == "Awaiting Assignment":
			self.status = "Assigned"
			self.add_activity("Lead teacher assigned")
		elif before and self.status == "Assigned" and self._teacher_content_changed():
			self.status = "In Preparation"

	def on_update(self):
		before = self.get_doc_before_save()
		if before and self.lead_teacher_user and self.lead_teacher_user != before.lead_teacher_user:
			self.notify_users([self.lead_teacher_user], _("You have been assigned an examination paper"))

	def _field_changed(self, before, fieldname):
		return self.get(fieldname) != before.get(fieldname)

	def _table_signature(self, fieldname, columns, doc=None):
		doc = doc or self
		values = []
		for row in doc.get(fieldname) or []:
			item = []
			for column in columns:
				value = row.get(column)
				if column == "maximum_score":
					value = flt(value)
				item.append(value)
			values.append(tuple(item))
		return tuple(values)

	def _criteria_signature(self, doc=None):
		return self._table_signature(
			"assessment_criteria", ("assessment_criteria", "maximum_score"), doc
		)

	def _teacher_content_changed(self):
		before = self.get_doc_before_save()
		if not before:
			return False
		return any(
			self.get(fieldname) != before.get(fieldname)
			for fieldname in (
				"blueprint_file",
				"question_paper_file",
				"marking_scheme_file",
				"duration_minutes",
				"teacher_notes",
			)
		) or self._criteria_signature() != self._criteria_signature(before)

	def add_activity(self, action, notes=None):
		self.append(
			"activity_history",
			{
				"action": action,
				"action_by": frappe.session.user,
				"action_on": now_datetime(),
				"notes": notes,
			},
		)

	def is_manager(self):
		return bool(set(frappe.get_roles()) & MANAGER_ROLES)

	def is_hod(self):
		return self.is_manager() or frappe.session.user == self.hod_user

	def is_assigned_teacher(self):
		return frappe.session.user == self.lead_teacher_user or frappe.session.user in {
			row.user for row in self.collaborators
		}

	def validate_submission_files(self):
		if self.blueprint_requirement == "Required" and not self.blueprint_file:
			frappe.throw(_("Attach the required Blueprint before submitting to the HOD."))
		if self.question_paper_required and not self.question_paper_file:
			frappe.throw(_("Attach the required Question Paper before submitting to the HOD."))
		if self.marking_scheme_required and not self.marking_scheme_file:
			frappe.throw(_("Attach the required Marking Scheme before submitting to the HOD."))
		if not self.assessment_criteria:
			frappe.throw(_("Add structured Assessment Criteria before submitting to the HOD."))

	def update_plan_coverage(self):
		created = 0
		for row in self.affected_student_groups:
			plan = frappe.db.get_value(
				"Assessment Plan",
				{
					"academic_year": self.academic_year,
					"assessment_group": self.assessment_group,
					"student_group": row.student_group,
					"course": self.course,
					"docstatus": ["<", 2],
				},
			)
			row.assessment_plan = plan
			row.plan_status = "Created" if plan else "Missing"
			created += int(bool(plan))
		self.expected_plan_count = len(self.affected_student_groups)
		self.created_plan_count = created
		self.missing_plan_count = self.expected_plan_count - created
		if self.status in PLAN_STATUSES and self.expected_plan_count:
			if created == self.expected_plan_count:
				self.status = "Complete"
			elif created:
				self.status = "Plans Partially Created"
			elif self.status in {"Plans Partially Created", "Complete"}:
				self.status = "Approved"

	@frappe.whitelist()
	def submit_to_hod(self):
		if not self.is_assigned_teacher() and not self.is_manager():
			frappe.throw(_("Only an assigned teacher can submit this examination paper."), frappe.PermissionError)
		if self.status not in TEACHER_EDITABLE_STATUSES:
			frappe.throw(_("This paper cannot be submitted while its status is {0}.").format(self.status))
		self.validate_submission_files()
		self.revision_number = (self.revision_number or 0) + 1
		self.submitted_by = frappe.session.user
		self.submitted_on = now_datetime()
		self.status = "Submitted to HOD"
		self.add_activity("Submitted to HOD", _("Revision {0}").format(self.revision_number))
		self.flags.in_workflow_action = True
		self.save(ignore_permissions=True)
		self.notify_users([self.hod_user], _("Exam paper awaiting HOD review"))
		return self.status

	@frappe.whitelist()
	def request_changes(self, notes):
		if not notes:
			frappe.throw(_("Enter the changes required."))
		if self.status == "Submitted to HOD" and not self.is_hod():
			frappe.throw(_("Only the assigned HOD can request changes at this stage."), frappe.PermissionError)
		if self.status == "Submitted to Exam Administration" and not self.is_manager():
			frappe.throw(_("Only an Education Manager can request changes at this stage."), frappe.PermissionError)
		if self.status not in {"Submitted to HOD", "Submitted to Exam Administration"}:
			frappe.throw(_("Changes cannot be requested while status is {0}.").format(self.status))
		self.latest_review_notes = notes
		self.status = "Changes Requested"
		self.add_activity("Changes requested", notes)
		self.flags.in_workflow_action = True
		self.save(ignore_permissions=True)
		self.notify_users([self.lead_teacher_user] + [row.user for row in self.collaborators], _("Exam paper changes required"))
		return self.status

	@frappe.whitelist()
	def approve_by_hod(self, notes=None):
		if not self.is_hod():
			frappe.throw(_("Only the assigned HOD can approve this paper."), frappe.PermissionError)
		if self.status != "Submitted to HOD":
			frappe.throw(_("The paper must be Submitted to HOD before HOD approval."))
		self.hod_approved_by = frappe.session.user
		self.hod_approved_on = now_datetime()
		self.latest_review_notes = notes
		self.status = "Submitted to Exam Administration"
		self.add_activity("Approved by HOD", notes)
		self.flags.in_workflow_action = True
		self.save(ignore_permissions=True)
		from high_school.high_school.exam_preparation import get_enabled_users_with_role

		self.notify_users(get_enabled_users_with_role("Education Manager"), _("Exam paper awaiting final approval"))
		return self.status

	@frappe.whitelist()
	def approve_by_admin(self, notes=None):
		if not self.is_manager():
			frappe.throw(_("Only an Education Manager can give final approval."), frappe.PermissionError)
		if self.status != "Submitted to Exam Administration":
			frappe.throw(_("The paper must have HOD approval before final approval."))
		self.admin_approved_by = frappe.session.user
		self.admin_approved_on = now_datetime()
		self.latest_review_notes = notes
		self.status = "Approved"
		self.add_activity("Approved by Exam Administration", notes)
		self.flags.in_workflow_action = True
		self.save(ignore_permissions=True)
		self.notify_users([self.lead_teacher_user, self.hod_user], _("Exam paper approved"))
		return self.status

	@frappe.whitelist()
	def refresh_plan_coverage(self):
		if not self.is_manager() and not self.is_hod():
			frappe.throw(_("Only the HOD or Education Manager can refresh plan coverage."), frappe.PermissionError)
		self.update_plan_coverage()
		self.flags.in_workflow_action = True
		self.save(ignore_permissions=True)
		return {
			"expected": self.expected_plan_count,
			"created": self.created_plan_count,
			"missing": self.missing_plan_count,
			"status": self.status,
		}

	@frappe.whitelist()
	def send_manual_reminder(self):
		if not self.is_hod():
			frappe.throw(_("Only the HOD or Education Manager can send a reminder."), frappe.PermissionError)
		recipients = [self.lead_teacher_user] if self.lead_teacher_user else [self.hod_user]
		self.notify_users(recipients, _("Action required for examination paper"))
		self.add_activity("Manual reminder sent")
		self.flags.in_workflow_action = True
		self.save(ignore_permissions=True)
		return True

	def notify_users(self, users, subject):
		from high_school.high_school.exam_preparation import create_exam_notification

		for user in {user for user in users if user and user != "Guest"}:
			create_exam_notification(user, subject, self)
