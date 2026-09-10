import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate


CLOSED_STATUSES = {"Closed - Successful", "Closed - Not Required"}
ACTION_REQUIRED_STATUSES = {"Action Planned", "In Progress", "Ready for Review", "Overdue", "Escalated"}


class StudentInterventionPlan(Document):
    def before_insert(self):
        self.opened_on = self.opened_on or now_datetime()

    def validate(self):
        self._validate_management_evidence()
        self._validate_actions()
        self._apply_follow_up_outcome()
        self._validate_closure()

    def _validate_management_evidence(self):
        if self.status in ACTION_REQUIRED_STATUSES | CLOSED_STATUSES:
            if not self.root_cause:
                frappe.throw(_("Select the Primary Root Cause before moving this plan forward."))
            if not self.diagnosis_notes:
                frappe.throw(_("Diagnosis Evidence and Notes are required before moving this plan forward."))
            if not self.review_date:
                frappe.throw(_("A Mandatory Review Date is required."))

        if self.review_date and getdate(self.review_date) < getdate(self.opened_on or nowdate()):
            frappe.throw(_("The Mandatory Review Date cannot be before the plan was opened."))

    def _validate_actions(self):
        if self.status in ACTION_REQUIRED_STATUSES | {"Closed - Successful"} and not self.actions:
            frappe.throw(_("Add at least one concrete intervention action."))
        for action in self.actions or []:
            if action.status == "Completed":
                if not action.completed_on:
                    action.completed_on = nowdate()
                if not action.completion_notes:
                    frappe.throw(_("Completion Evidence / Notes are required for completed actions."))
            elif action.status != "Cancelled":
                action.completed_on = None

    def _apply_follow_up_outcome(self):
        if self.status != "Ready for Review" or self.follow_up_value in (None, ""):
            return
        if not self.follow_up_evidence:
            frappe.throw(_("Enter the follow-up assessment or attendance evidence before recording its result."))
        improved = (
            float(self.follow_up_value) > float(self.baseline_value or 0)
            if self.metric_direction == "Higher is Better"
            else float(self.follow_up_value) < float(self.baseline_value or 0)
        )
        if improved:
            self.outcome = self.outcome or "Improved - Continue Monitoring"
            return

        # A completed review that did not improve is an escalation, not a
        # successful closure. The principal becomes accountable immediately.
        from high_school.high_school.mis.settings import get_mis_settings

        principal = get_mis_settings().get("school_principal_user")
        self.status = "Escalated"
        self.outcome = "No Improvement - Escalated"
        self.escalated_to = principal or self.hod_user or self.assigned_to
        self.escalated_on = self.escalated_on or now_datetime()

    def _validate_closure(self):
        if self.status not in CLOSED_STATUSES:
            self.closed_on = None
            return
        if not self.resolution_notes:
            frappe.throw(_("Resolution / Next-step Notes are required before closing the plan."))

        if self.status == "Closed - Successful":
            incomplete = [row for row in self.actions if row.status not in {"Completed", "Cancelled"}]
            if incomplete:
                frappe.throw(_("Complete or cancel every assigned action before closing this plan as successful."))
            if self.follow_up_value is None or self.follow_up_value == "":
                frappe.throw(_("Enter the Follow-up Value before closing this plan as successful."))
            if not self.follow_up_evidence:
                frappe.throw(_("Link or describe the follow-up assessment or attendance evidence."))
            improved = (
                float(self.follow_up_value) > float(self.baseline_value or 0)
                if self.metric_direction == "Higher is Better"
                else float(self.follow_up_value) < float(self.baseline_value or 0)
            )
            if not improved:
                frappe.throw(
                    _("The follow-up result has not improved from the baseline. Continue the plan or escalate it.")
                )
            self.outcome = self.outcome or "Improved - Target Met"

        self.closed_on = self.closed_on or now_datetime()
        self.resolved_evidence_count = self.evidence_count or 0

    def on_update(self):
        before = self.get_doc_before_save()
        previous_assignees = {
            row.assigned_to for row in (before.actions if before else []) if row.assigned_to
        }
        new_assignees = {row.assigned_to for row in self.actions if row.assigned_to} - previous_assignees
        for user in new_assignees:
            _notify_user(user, _("Student intervention action assigned"), self)
            from high_school.high_school.student_interventions import assign_plan_todo

            action = next(row for row in self.actions if row.assigned_to == user)
            assign_plan_todo(
                user,
                self,
                _("Intervention action: {0}").format(action.action_type),
                action.due_date,
            )
        was_escalated = before and before.status == "Escalated"
        if self.status == "Escalated" and not was_escalated:
            escalation_owner = self.escalated_to or self.hod_user or self.assigned_to
            _notify_user(escalation_owner, _("Student intervention escalated after review"), self)
            from high_school.high_school.student_interventions import assign_plan_todo

            assign_plan_todo(
                escalation_owner,
                self,
                _("Review escalated student intervention"),
                self.review_date,
            )
        if self.status in CLOSED_STATUSES:
            for todo in frappe.get_all(
                "ToDo",
                filters={
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                    "status": "Open",
                },
                pluck="name",
            ):
                frappe.db.set_value("ToDo", todo, "status", "Closed")


def _notify_user(user, subject, doc):
    if not user or user == "Guest":
        return
    notification = frappe.new_doc("Notification Log")
    notification.for_user = user
    notification.from_user = frappe.session.user
    notification.subject = subject
    notification.type = "Alert"
    notification.document_type = doc.doctype
    notification.document_name = doc.name
    notification.insert(ignore_permissions=True)
