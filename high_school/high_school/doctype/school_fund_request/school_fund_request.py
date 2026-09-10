import frappe

from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


APPROVED_STATUSES = {"Approved", "Partly Disbursed", "Disbursed"}


class SchoolFundRequest(Document):
    def validate(self):
        requested = flt(self.requested_amount)
        approved = flt(self.approved_amount)
        disbursed = flt(self.disbursed_amount)
        if min(requested, approved, disbursed) < 0:
            frappe.throw(_("Fund request amounts cannot be negative."))
        if approved > requested:
            frappe.throw(_("Approved Amount cannot exceed Requested Amount."))
        if disbursed > approved:
            frappe.throw(_("Disbursed Amount cannot exceed Approved Amount."))
        if self.status in APPROVED_STATUSES and not approved:
            frappe.throw(_("Approved Amount is required for this status."))
        if self.status in {"Partly Disbursed", "Disbursed"} and not disbursed:
            frappe.throw(_("Disbursed Amount is required for this status."))
        if self.status == "Disbursed" and disbursed != approved:
            frappe.throw(
                _("A Disbursed request must have its full Approved Amount paid.")
            )
        if disbursed and not any(
            (self.purchase_invoice, self.payment_entry, self.journal_entry)
        ):
            frappe.throw(
                _(
                    "Link a submitted Purchase Invoice, Payment Entry, or "
                    "Journal Entry before recording a disbursement."
                )
            )
        for doctype, name in (
            ("Purchase Invoice", self.purchase_invoice),
            ("Payment Entry", self.payment_entry),
            ("Journal Entry", self.journal_entry),
        ):
            if name and frappe.db.get_value(doctype, name, "docstatus") != 1:
                frappe.throw(
                    _("Linked {0} {1} must be submitted.").format(doctype, name)
                )
        if self.status in APPROVED_STATUSES and not self.approved_on:
            self.approved_on = now_datetime()
            self.approved_by = frappe.session.user
        self.outstanding_amount = (
            0
            if self.status in {"Rejected", "Cancelled"}
            else max(0, approved - disbursed)
        )
        self.progress = round((disbursed / approved) * 100, 1) if approved else 0
