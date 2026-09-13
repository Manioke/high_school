"""Keep Education Instructor departures aligned with Frappe HR."""

import frappe
from frappe.utils import today


def setup_employee_instructor_field():
    """Install the opt-in Employee to Instructor automation field."""
    if frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": "custom_create_instructor_automatically"}):
        return
    employee_fields = {field.fieldname for field in frappe.get_meta("Employee").fields}
    insert_after = next((field for field in ("create_user_permission", "user_id", "company") if field in employee_fields), "company")
    frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Employee",
        "module": "High School",
        "fieldname": "custom_create_instructor_automatically",
        "label": "Create Instructor Automatically",
        "fieldtype": "Check",
        "insert_after": insert_after,
        "description": "After this Employee is saved, create and link an Education Instructor if one does not already exist.",
    }).insert(ignore_permissions=True)
    frappe.db.commit()


def create_instructor_from_employee(doc, method=None):
    """Create one linked Instructor when the Employee explicitly requests it."""
    if not doc.get("custom_create_instructor_automatically") or not doc.get("name"):
        return
    if not frappe.db.exists("DocType", "Instructor"):
        return
    if frappe.db.exists("Instructor", {"employee": doc.name}):
        return
    fields = {field.fieldname for field in frappe.get_meta("Instructor").fields}
    instructor = frappe.new_doc("Instructor")
    instructor.instructor_name = doc.employee_name
    if "employee" in fields:
        instructor.employee = doc.name
    if "department" in fields:
        instructor.department = doc.get("department")
    if "gender" in fields:
        instructor.gender = doc.get("gender")
    if "status" in fields:
        instructor.status = "Left" if doc.get("status") == "Left" else "Active"
    if "user_id" in fields and doc.get("user_id"):
        instructor.user_id = doc.user_id
    elif "user" in fields and doc.get("user_id"):
        instructor.user = doc.user_id
    instructor.insert(ignore_permissions=True)


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
