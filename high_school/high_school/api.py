import frappe
import json
import education.education.api 
from education.education.doctype.student_leave_application.student_leave_application import StudentLeaveApplication
from education.education.doctype.student_attendance.student_attendance import get_holiday_list
from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday
from frappe.utils import data, getdate, add_days, date_diff
from urllib.parse import unquote
from datetime import timedelta
from frappe import _
import re

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
    
    identifier = unquote(str(identifier))
    
    # Check if this is an "Option" group or a "Main" group
    is_option_group = any(x in identifier for x in ["Opt1", "Opt2", "Opt3", "Opt4"])

    # CASE 1: It's an Option Group (Your custom High School logic)
    if is_option_group:
        student = frappe.qb.DocType("Student")
        pe = frappe.qb.DocType("Program Enrollment")
        
        option_field = None
        if "Opt1" in identifier: option_field = student.custom_option_1
        elif "Opt2" in identifier: option_field = student.custom_option_2
        elif "Opt3" in identifier: option_field = student.custom_option_3
        elif "Opt4" in identifier: option_field = student.custom_option_4

        query = (
            frappe.qb.from_(pe)
            .join(student).on(pe.student == student.name)
            .select(pe.student, pe.student_name)
            .where(pe.academic_year == data.get('academic_year'))
            .where(pe.docstatus == 1)
            .where(option_field == data.get('course'))
        )
        
        if data.get('program'): query = query.where(pe.program == data.get('program'))
        if data.get('batch'): query = query.where(pe.student_batch_name == data.get('batch'))

        res = query.run(as_dict=1)
        for d in res:
            d.active = 1 if frappe.db.get_value("Student", d.student, "enabled") else 0
        return res

    # CASE 2: It's a Main Group (Standard Frappe Education logic)
    else:
        from education.education.doctype.student_group.student_group import get_students
        # Fallback to the original Frappe function you pasted above
        return get_students(
            academic_year=data.get('academic_year'),
            group_based_on=data.get('group_based_on'),
            academic_term=data.get('academic_term'),
            program=data.get('program'),
            batch=data.get('batch'),
            student_category=data.get('student_category'),
            course=data.get('course')
        )

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
    form_code = ""
    if "TVET" in doc.student_batch_name:
        form_code = "TV"
    else:
        digit = re.findall(r'\d+', doc.student_batch_name)
        if digit:
            form_code = f"F0{digit[0]}"
    
    # 3. Check Global Setting for Sibling Rank
    use_sibling_rank = frappe.db.get_single_value("Education Settings", "custom_use_sibling_ranking")
    
    rank = ""
    if use_sibling_rank:
        # Pull rank from Student profile, fallback safely if empty
        rank = frappe.db.get_value("Student", doc.student, "custom_sibling_rank") or "C01"
    
    # 4. Construct the Final Fee Structure Target Name
    # With toggle ON:  "NF01C02"
    # With toggle OFF: "NF01"
    target_fee_structure = f"{stream}{form_code}{rank}"
    
    # 5. Fetch the Matching Active Fee Schedule
    fee_schedule = frappe.db.get_value("Fee Schedule", {
        "fee_structure": target_fee_structure,
        "academic_term": doc.academic_term,
        "docstatus": 1
    }, "name")
    
    if not fee_schedule:
        frappe.throw(_("No active Fee Schedule found for {0} in {1}").format(target_fee_structure, doc.academic_term))
    
    # 6. Generate the standard Core Sales Invoice
    invoice_name = create_sales_invoice(fee_schedule, doc.student)
    msg = f"Sales Invoice {invoice_name} created for {target_fee_structure}"

    # 7. Apply Dynamic Percentage Discounts (e.g., Teacher's Child, Sports Scholarship)
    discount_pct = frappe.db.get_value("Student", doc.student, "custom_fee_discount_percentage")
    
    if discount_pct and float(discount_pct) > 0:
        discount_factor = float(discount_pct) / 100.0
        
        # Load the newly created Sales Invoice draft or document
        si_doc = frappe.get_doc("Sales Invoice", invoice_name)
        
        # Apply the markdown across item rows
        for item in si_doc.items:
            item.discount_percentage = float(discount_pct)
            # Re-calculate rate based on the assigned discount value
            item.amount = item.rate * item.qty * (1 - discount_factor)
            
        # Recompute grand totals across tax schedules and sums safely
        si_doc.flags.ignore_validate_update_after_submit = True
        si_doc.save(ignore_permissions=True)
        
        msg += f" with a {discount_pct}% custom staff/scholarship discount applied."

    frappe.msgprint(msg)

## This function is triggered on submission of Program Enrollment to update Student fields based on the enrollment details.

def update_student_fields(doc, method=None):
    """
    Triggered 'on_submit' of Program Enrollment.
    Transfers:
      - student_category -> custom_section (in Student)
      - student_batch_name -> custom_form (in Student)
    """
    if not doc.student:
        return

    # Check if the Student record exists
    if frappe.db.exists("Student", doc.student):
        
        # Scenario A: Fast update directly to the Database (Doesn't trigger Student validation hooks)
        frappe.db.set_value("Student", doc.student, {
            "custom_section": doc.student_category,
            "custom_form": doc.student_batch_name
        })
        
        # Scenario B: Alternative approach if you need Student's own validation rules to run:
        # student_doc = frappe.get_doc("Student", doc.student)
        # student_doc.custom_section = doc.student_category
        # student_doc.custom_form = doc.student_batch_name
        # student_doc.save(ignore_permissions=True)
        
        # Optional: Add a small status message for the user
        frappe.msgprint(frappe._("Student {0} fields updated successfully.").format(doc.student))

## This function is triggered on saving a Student Applicant to sync sibling rank back to the Student record if it's an Old Student application being approved.
def sync_old_student_rank_on_approval(doc, method=None):
    """
    Runs before Student Applicant saves.
    If an 'Old Student' application is being set to 'Approved',
    sync the custom_sibling_rank back to the master Student record.
    """
    if doc.custom_application_type == "Old Student" and doc.custom_student_id:
        # Check if the status was just changed to Approved
        # (frappe.db.get_value checks the current value sitting in the database before this save)
        old_status = frappe.db.get_value("Student Applicant", doc.name, "application_status")
        
        if doc.application_status == "Approved" and old_status != "Approved":
            # Push the updated sibling rank from the applicant form to the master Student Doctype
            frappe.db.set_value(
                "Student", 
                doc.custom_student_id, 
                "custom_sibling_rank", 
                doc.custom_sibling_rank
            )
            frappe.msgprint(
                frappe._("Master Student record updated with new Sibling Rank: {0}")
                .format(doc.custom_sibling_rank)
            )
## This function is designed to be run once, perhaps via hooks.py and after_migrate, to ensure the custom field for sibling ranking exists in the Education Settings doctype.
def create_education_settings_custom_field():
    """
    Programmatically inserts the custom checkbox field into the 
    Education Settings Single Doctype if it doesn't already exist.
    """
    field_fieldname = "custom_use_sibling_ranking"
    
    # Check if the field already exists to avoid duplicates
    if not frappe.db.exists("Custom Field", {"dt": "Education Settings", "fieldname": field_fieldname}):
        
        # Insert the custom field record directly into the system
        custom_field = frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Education Settings",
            "fieldname": field_fieldname,
            "label": "Use Sibling Ranking Matrix",
            "fieldtype": "Check",
            "insert_after": "user_creation_skip", # Positions it cleanly in the UI
            "description": "Toggle ON for FWC style sibling ranking, toggle OFF for standard Form levels."
        })
        custom_field.insert(ignore_permissions=True)
        frappe.db.commit() 
        