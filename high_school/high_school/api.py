import frappe
import json
import education.education.api 
from education.education.doctype.student_leave_application.student_leave_application import StudentLeaveApplication
from education.education.doctype.student_attendance.student_attendance import get_holiday_list
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from frappe.utils import getdate, add_days, date_diff
from urllib.parse import unquote
from datetime import timedelta

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
    present = json.loads(students_present)
    absent = json.loads(students_absent)

    for s in present + absent:
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
    data = frappe._dict(kwargs if kwargs else frappe.local.form_dict)
    identifier = data.get('student_group') or data.get('student_group_name')
    
    if not identifier:
        referrer = frappe.local.request.referrer or ""
        if 'student-group/' in referrer:
            identifier = referrer.split('student-group/')[-1].split('?')[0]
    
    if not identifier:
        frappe.throw("Could not detect Student Group Name.")

    identifier = unquote(str(identifier))
    course = data.get('course')
    academic_year = data.get('academic_year')
    
    student = frappe.qb.DocType("Student")
    pe = frappe.qb.DocType("Program Enrollment")
    
    option_field = None
    if "Opt1" in identifier: option_field = student.custom_option_1
    elif "Opt2" in identifier: option_field = student.custom_option_2
    elif "Opt3" in identifier: option_field = student.custom_option_3
    elif "Opt4" in identifier: option_field = student.custom_option_4
        
    if not option_field:
        frappe.throw(f"Group '{identifier}' needs Opt1-Opt4 in its name.")

    query = (
        frappe.qb.from_(pe)
        .join(student).on(pe.student == student.name)
        .select(pe.student, pe.student_name)
        .where(pe.academic_year == academic_year)
        .where(pe.docstatus == 1)
        .where(option_field == course)
    )
    
    if data.get('program'): query = query.where(pe.program == data.get('program'))
    if data.get('batch'): query = query.where(pe.student_batch_name == data.get('batch'))

    res = query.run(as_dict=1)
    for d in res:
        d.active = frappe.db.get_value("Student", d.student, "enabled")

    return res

# --- 1. MONKEY PATCHES ---

def custom_make_attendance_records(student, student_name, status, course_schedule=None, student_group=None, date=None):
    cs_filter = course_schedule if course_schedule else ["is", "not set"]
    existing_name = frappe.db.exists("Student Attendance", {
        "student": student,
        "course_schedule": cs_filter,
        "student_group": student_group,
        "date": date,
        "docstatus": ["<", 2]
    })

    if existing_name:
        curr_status = frappe.db.get_value("Student Attendance", existing_name, "status")
        if curr_status == "Leave":
            return 
        frappe.db.set_value("Student Attendance", existing_name, "status", status)
    else:
        doc = frappe.new_doc("Student Attendance")
        doc.student = student
        doc.student_name = student_name
        doc.course_schedule = course_schedule
        doc.student_group = student_group
        doc.date = date
        doc.status = status
        doc.insert(ignore_permissions=True, ignore_mandatory=True)
        doc.submit()

@frappe.whitelist()
def custom_mark_attendance(students_present, students_absent, course_schedule=None, student_group=None, date=None):
    present = json.loads(students_present)
    absent = json.loads(students_absent)

    for d in present:
        custom_make_attendance_records(d["student"], d["student_name"], "Present", course_schedule, student_group, date)
    for d in absent:
        custom_make_attendance_records(d["student"], d["student_name"], "Absent", course_schedule, student_group, date)

    frappe.db.commit()
    frappe.msgprint("Attendance has been marked successfully.testing")

education.education.api.make_attendance_records = custom_make_attendance_records
education.education.api.mark_attendance = custom_mark_attendance

# --- 2. LEAVE APPLICATION OVERRIDE ---

@frappe.whitelist()
def update_attendance_on_leave_approval(doc, method=None):
    # 1. Get all Student Groups the student is part of
    student_groups = frappe.get_all("Student Group Student", 
        filters={"student": doc.student, "active": 1}, 
        pluck="parent"
    )

    if not student_groups:
        return

    current_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    # 2. Iterate through each day of the leave
    while current_date <= to_date:
        # 3. Find all Course Schedules (Removed docstatus filter so it finds everything)
        schedules = frappe.get_all("Course Schedule",
            filters={
                "student_group": ["in", student_groups],
                "schedule_date": current_date
                # No docstatus filter here makes it more inclusive
            },
            fields=["name", "student_group"]
        )

        for sch in schedules:
            # 4. Check if attendance already exists
            existing = frappe.db.exists("Student Attendance", {
                "student": doc.student,
                "course_schedule": sch.name,
                "date": current_date,
                "docstatus": ["<", 2] # Don't look at cancelled records
            })

            if existing:
                # 5. FLIP: Update existing record (e.g. Absent -> Leave)
                frappe.db.set_value("Student Attendance", existing, {
                    "status": "Leave",
                    "leave_application": doc.name,
                    "student_group": sch.student_group
                })
            else:
                # 6. CREATE: Only if it absolutely doesn't exist
                try:
                    attendance = frappe.get_doc({
                        "doctype": "Student Attendance",
                        "student": doc.student,
                        "student_name": doc.student_name,
                        "date": current_date,
                        "status": "Leave",
                        "student_group": sch.student_group,
                        "course_schedule": sch.name,
                        "leave_application": doc.name
                    })
                    attendance.insert(ignore_permissions=True)
                    attendance.submit()
                except Exception:
                    pass

        current_date = add_days(current_date, 1)

from education.education.doctype.fee_schedule.fee_schedule import create_sales_invoice

def generate_custom_fees(doc, method):
    # 1. Determine Stream Prefix
    stream = "I" if doc.student_category == "INT" else "N"
    
    # 2. Determine Form/Level
    # Logic: "Form 1 - 2026" -> "F01", "TVET - 2026" -> "TV"
    form_code = ""
    if "TVET" in doc.student_batch_name:
        form_code = "TV"
    else:
        # Extracts '01' from 'Form 1' and adds 'F'
        import re
        digit = re.findall(r'\d+', doc.student_batch_name)
        if digit:
            form_code = f"F0{digit[0]}"
    
    # 3. Get Sibling Rank from Student (assuming it was mapped from Applicant)
    rank = frappe.db.get_value("Student", doc.student, "custom_sibling_rank") or "C01"
    
    # 4. Construct the Final Fee Structure Name
    # Example: I + F01 + C02 = IF01C02
    target_fee_structure = f"{stream}{form_code}{rank}"
    
    # 5. Find a Fee Schedule linked to this structure for the current term
    fee_schedule = frappe.db.get_value("Fee Schedule", {
        "fee_structure": target_fee_structure,
        "academic_term": doc.academic_term,
        "docstatus": 1
    }, "name")
    
    if fee_schedule:
        create_sales_invoice(fee_schedule, doc.student)
        frappe.msgprint(f"Sales Invoice created for {target_fee_structure}")
    else:
        frappe.throw(f"No active Fee Schedule found for {target_fee_structure} in {doc.academic_term}")