import frappe
from frappe.utils import today

@frappe.whitelist()
def get_taliui_records(house, date, taliui):
    # 1. Get all students in the House
    student_list = frappe.get_all("Student",
        fields=["name as student", "student_name"],
        filters={"custom_falemohe": house, "enabled": 1},
        order_by="student_name"
    )

    # 2. Get existing Taliui records for this date/shift
    TaliuiDoc = frappe.qb.DocType("Taliui Akonofo")
    existing_attendance = (
        frappe.qb.from_(TaliuiDoc)
        .select(TaliuiDoc.student, TaliuiDoc.status)
        .where(
            (TaliuiDoc.house == house) & 
            (TaliuiDoc.date == date) & 
            (TaliuiDoc.taliui == taliui)
        )
    ).run(as_dict=True)

    # 3. Check for approved Leave
    for student in student_list:
        student.status = "Absent" # Default
        
        # Mark as Present if record exists
        for att in existing_attendance:
            if att.student == student.student:
                student.status = att.status

        # Override with Leave if applicable
        on_leave = frappe.db.exists("Student Leave Application", {
            "student": student.student,
            "start_date": ["<=", date],
            "end_date": [">=", date],
            "docstatus": 1
        })
        if on_leave:
            student.status = "Leave"

    return student_list

@frappe.whitelist()
def mark_taliui_attendance(students_present, students_absent, house, taliui, date):
    import json
    present = json.loads(students_present)
    absent = json.loads(students_absent)

    for s in present + absent:
        # Check if record already exists to update or insert
        existing_name = frappe.db.get_value("Taliui Akonofo", {
            "student": s['student'],
            "date": date,
            "taliui": taliui
        })

        status = "Present" if s.get('checked') else "Absent"
        
        if existing_name:
            doc = frappe.get_doc("Taliui Akonofo", existing_name)
            doc.status = status
            doc.save()
        else:
            frappe.get_doc({
                "doctype": "Taliui Akonofo",
                "student": s['student'],
                "taliui": taliui,
                "date": date,
                "status": status,
                "house": house
            }).insert()
    
    return True