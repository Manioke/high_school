import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate


CLOSED_STATUSES = {"Closed - Successful", "Closed - Not Required"}
ACTION_REQUIRED_STATUSES = {
    "Action Planned", "In Progress", "Monitoring", "Ready for Review",
    "Overdue", "Escalated",
}


class StudentInterventionPlan(Document):
    def before_insert(self):
        self.opened_on = self.opened_on or now_datetime()

    def validate(self):
        if self.is_new() and not self.course:
            frappe.throw(_("Course is required for every new Student Intervention Plan."))
        self._set_monitoring_start()
        self._validate_management_evidence()
        self._validate_actions()
        self._validate_closure()

    def _set_monitoring_start(self):
        before = self.get_doc_before_save()
        previous_status = before.status if before else None
        monitored = {"Action Planned", "In Progress", "Monitoring", "Ready for Review"}
        if self.status in monitored and previous_status not in monitored:
            self.monitoring_started_on = self.monitoring_started_on or now_datetime()

    def _validate_management_evidence(self):
        before = self.get_doc_before_save()
        if (
            self.status == "Escalated"
            and (not before or before.status != "Escalated")
            and not self.escalation_reason
        ):
            frappe.throw(_("Use the Escalate button so an escalation reason and notifications are recorded."))
        automatic_close = (
            self.status == "Closed - Successful"
            and self.comparison_summary
            and float(self.percentage_point_change or 0) > 0
        )
        automatic_escalation = self.status == "Escalated" and self.escalation_reason
        if automatic_close or automatic_escalation:
            return
        if self.status in ACTION_REQUIRED_STATUSES | CLOSED_STATUSES:
            if not self.root_cause:
                frappe.throw(_("Select the Primary Root Cause before moving this plan forward."))
            if not self.diagnosis_notes:
                frappe.throw(_("Diagnosis Evidence and Notes are required before moving this plan forward."))

    def _validate_actions(self):
        automatic_outcome = (
            (self.status == "Closed - Successful" and self.comparison_summary)
            or (self.status == "Escalated" and self.escalation_reason)
        )
        if (
            self.status in ACTION_REQUIRED_STATUSES | {"Closed - Successful"}
            and not self.actions
            and not automatic_outcome
        ):
            frappe.throw(_("Add at least one concrete intervention action."))
        for action in self.actions or []:
            if action.status == "Completed":
                if not action.completed_on:
                    action.completed_on = nowdate()
                if not action.completion_notes:
                    frappe.throw(_("Completion Evidence / Notes are required for completed actions."))
            elif action.status != "Cancelled":
                action.completed_on = None

    def _validate_closure(self):
        if self.status not in CLOSED_STATUSES:
            self.closed_on = None
            return
        if not self.resolution_notes:
            frappe.throw(_("Resolution / Next-step Notes are required before closing the plan."))

        if self.status == "Closed - Successful":
            if self.intervention_type != "Academic" or not self.comparison_summary:
                frappe.throw(_("Successful closure is set automatically from the next submitted Student Performance Summary."))
            if float(self.percentage_point_change or 0) <= 0:
                frappe.throw(_("The next overall performance result did not improve."))
            self.outcome = self.outcome or "Improved - Continue Monitoring"

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
        if self.status == "Escalated" and not was_escalated and not self.escalation_reason:
            escalation_owner = self.escalated_to or self.hod_user or self.assigned_to
            _notify_user(escalation_owner, _("Student intervention escalated after review"), self)
            from high_school.high_school.student_interventions import assign_plan_todo

            assign_plan_todo(
                escalation_owner,
                self,
                _("Review escalated student intervention"),
                nowdate(),
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
