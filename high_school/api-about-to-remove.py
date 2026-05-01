import frappe
from frappe.utils import today

@frappe.whitelist()
def get_students_by_house(house):
    # Fetch students in the house
    students = frappe.get_all("Student", 
        filters={"custom_falemohe": house, "enabled": 1}, 
        fields=["name", "student_name"])
    
    # Check for approved Leave
    for s in students:
        leave_exists = frappe.db.exists("Student Leave Application", {
            "student": s.name,
            "start_date": ["<=", today()],
            "end_date": [">=", today()],
            "docstatus": 1
        })
        s["on_leave"] = True if leave_exists else False
        
    return students

@frappe.whitelist()
def submit_taliui_bulk(house, shift, date, attendance_json):
    import json
    records = json.loads(attendance_json)
    
    for r in records:
        doc = frappe.get_doc({
            "doctype": "Taliui Akonofo",
            "student": r['student'],
            "taliui": shift,
            "date": date,
            "status": r['status'],
            "house": house
        })
        doc.insert()
    return True