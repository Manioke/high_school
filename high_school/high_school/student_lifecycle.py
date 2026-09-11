"""Student departure and option-course lifecycle automation."""

import frappe
from frappe.utils import cint

OPTION_FIELDS = tuple(f"custom_option_{index}" for index in range(1, 5))


def prepare_student_departure(doc, method=None):
    """A Student with a leaving date is no longer enabled."""
    leaving_changed = bool(doc.get("date_of_leaving")) and (
        doc.is_new() or doc.has_value_changed("date_of_leaving") or cint(doc.get("enabled"))
    )
    if leaving_changed:
        doc.enabled = 0
        doc.flags.high_school_departure_changed = True


def handle_student_update(doc, method=None):
    """Reconcile groups and departure accounting after save."""
    from high_school.high_school.student_group_sync import queue_student_group_refresh

    option_changed = doc.is_new() or any(doc.has_value_changed(field) for field in OPTION_FIELDS)
    if option_changed or any(doc.get(field) for field in OPTION_FIELDS) or doc.flags.get(
        "high_school_departure_changed"
    ):
        queue_student_group_refresh()

    if doc.flags.get("high_school_departure_changed"):
        # This must be immediate.  A background worker may be disabled on a
        # small school site, which previously left the invoices untouched even
        # though the Student was successfully disabled.
        cancel_departed_student_invoices(doc.name)


def _student_invoice_filters(student):
    """Return safe Sales Invoice filters for every supported Student link."""
    invoice_fields = {field.fieldname for field in frappe.get_meta("Sales Invoice").fields}
    student_fields = {field.fieldname for field in frappe.get_meta("Student").fields}
    common = {
        "docstatus": 1,
        "outstanding_amount": [">", 0],
    }
    filters = []

    # Frappe Education normally records both Student and Customer on the
    # invoice.  Keep the direct Student link as the strongest match.
    if "student" in invoice_fields:
        filters.append({**common, "student": student})

    # Some existing/imported invoices only retain the Customer link.  Resolve
    # that Customer from the Student master instead of assuming that the
    # Customer name equals the Student ID.
    customer = None
    if "customer" in student_fields:
        customer = frappe.db.get_value("Student", student, "customer")
    if customer and "customer" in invoice_fields:
        filters.append({**common, "customer": customer})

    return filters


def cancel_departed_student_invoices(student):
    """Cancel submitted, wholly unpaid invoices for a departed Student."""
    if not frappe.db.get_value("Student", student, "date_of_leaving"):
        return {"cancelled": [], "failed": []}

    invoice_names = set()
    for filters in _student_invoice_filters(student):
        invoice_names.update(
            frappe.get_all(
                "Sales Invoice",
                filters=filters,
                pluck="name",
                limit_page_length=0,
            )
        )
    cancelled = []
    failed = []
    for name in sorted(invoice_names):
        invoice = frappe.get_doc("Sales Invoice", name)
        # Do not cancel an invoice with any allocated payment.
        invoice_total = invoice.get("rounded_total") or invoice.get("grand_total") or 0
        if abs(float(invoice.outstanding_amount or 0) - float(invoice_total)) > 0.01:
            continue
        try:
            invoice.flags.ignore_permissions = True
            invoice.cancel()
            cancelled.append(name)
        except Exception:
            failed.append(name)
            frappe.log_error(
                title=f"Could not cancel departed Student invoice {name}",
                message=frappe.get_traceback(),
            )
    return {"cancelled": cancelled, "failed": failed}
