"""Keep Education Instructor departures aligned with Frappe HR."""

import frappe
from frappe.utils import today


def sync_instructor_departure(doc, method=None):
    """Mark the linked Employee Left when an Instructor is marked Left."""
    if doc.get("status") != "Left" or not doc.get("employee"):
        return
    if not frappe.db.exists("Employee", doc.employee):
        return

    employee = frappe.get_doc("Employee", doc.employee)
    changed = False
    if employee.get("status") != "Left":
        employee.status = "Left"
        changed = True
    if employee.meta.has_field("relieving_date") and not employee.get("relieving_date"):
        employee.relieving_date = doc.get("date_of_leaving") or today()
        changed = True
    if changed:
        employee.flags.ignore_permissions = True
        employee.save(ignore_permissions=True)
