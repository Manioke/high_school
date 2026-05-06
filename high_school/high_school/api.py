import frappe
from frappe.utils import today
from urllib.parse import unquote

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

@frappe.whitelist()
def get_students_custom(*args, **kwargs):
    # Use kwargs first, fall back to form_dict
    data = frappe._dict(kwargs if kwargs else frappe.local.form_dict)
    
    # 1. Get identifier from args OR from the URL Referrer
    identifier = data.get('student_group') or data.get('student_group_name')
    
    if not identifier:
        # If the JS didn't send it, grab it from the URL: 
        # http://.../student-group/F5-COM-Opt1-2026
        referrer = frappe.local.request.referrer or ""
        if 'student-group/' in referrer:
            identifier = referrer.split('student-group/')[-1].split('?')[0]
    
    if not identifier:
        frappe.throw("Could not detect Student Group Name from request or URL.")

    identifier = unquote(str(identifier))
    
    # 2. Extract core filters
    course = data.get('course')
    academic_year = data.get('academic_year')
    
    # 3. Database logic
    student = frappe.qb.DocType("Student")
    pe = frappe.qb.DocType("Program Enrollment")
    
    # Map Option field
    option_field = None
    if "Opt1" in identifier:
        option_field = student.custom_option_1
    elif "Opt2" in identifier:
        option_field = student.custom_option_2
    elif "Opt3" in identifier:
        option_field = student.custom_option_3
    elif "Opt4" in identifier:
        option_field = student.custom_option_4
        
    if not option_field:
        frappe.throw(f"Group '{identifier}' needs Opt1, Opt2, Opt3, or Opt4 in its name.")

    # 4. The Query
    query = (
        frappe.qb.from_(pe)
        .join(student).on(pe.student == student.name)
        .select(pe.student, pe.student_name)
        .where(pe.academic_year == academic_year)
        .where(pe.docstatus == 1)
        .where(option_field == course)
    )
    
    if data.get('program'):
        query = query.where(pe.program == data.get('program'))
    if data.get('batch'):
        query = query.where(pe.student_batch_name == data.get('batch'))

    res = query.run(as_dict=1)

    for d in res:
        d.active = frappe.db.get_value("Student", d.student, "enabled")

    return res