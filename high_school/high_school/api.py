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
    student_groups = frappe.get_all("Student Group Student", 
        filters={"student": doc.student, "active": 1}, 
        pluck="parent"
    )

    if not student_groups:
        return

    current_date = getdate(doc.from_date)
    to_date = getdate(doc.to_date)

    while current_date <= to_date:
        schedules = frappe.get_all("Course Schedule",
            filters={
                "student_group": ["in", student_groups],
                "schedule_date": current_date
            },
            fields=["name", "student_group"]
        )

        for sch in schedules:
            existing = frappe.db.exists("Student Attendance", {
                "student": doc.student,
                "course_schedule": sch.name,
                "date": current_date,
                "docstatus": ["<", 2]
            })

            if existing:
                frappe.db.set_value("Student Attendance", existing, {
                    "status": "Leave",
                    "leave_application": doc.name,
                    "student_group": sch.student_group
                })
            else:
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
    stream = "I" if doc.student_category == "INT" else "N"
    
    form_code = ""
    if "TVET" in doc.student_batch_name:
        form_code = "TV"
    else:
        digit = re.findall(r'\d+', doc.student_batch_name)
        if digit:
            form_code = f"F0{digit[0]}"
    
    use_sibling_rank = frappe.db.get_single_value("Education Settings", "custom_use_sibling_ranking")
    
    rank = ""
    if use_sibling_rank:
        rank = frappe.db.get_value("Student", doc.student, "custom_sibling_rank") or "C01"
    
    target_fee_structure = f"{stream}{form_code}{rank}"
    
    fee_schedule = frappe.db.get_value("Fee Schedule", {
        "fee_structure": target_fee_structure,
        "academic_term": doc.academic_term,
        "docstatus": 1
    }, "name")
    
    if not fee_schedule:
        frappe.throw(_("No active Fee Schedule found for {0} in {1}").format(target_fee_structure, doc.academic_term))
    
    invoice_name = create_sales_invoice(fee_schedule, doc.student)
    msg = f"Sales Invoice {invoice_name} created for {target_fee_structure}"

    discount_pct = frappe.db.get_value("Student", doc.student, "custom_fee_discount_percentage")
    
    if discount_pct and float(discount_pct) > 0:
        discount_factor = float(discount_pct) / 100.0
        si_doc = frappe.get_doc("Sales Invoice", invoice_name)
        
        for item in si_doc.items:
            item.discount_percentage = float(discount_pct)
            item.amount = item.rate * item.qty * (1 - discount_factor)
            
        si_doc.flags.ignore_validate_update_after_submit = True
        si_doc.save(ignore_permissions=True)
        
        msg += f" with a {discount_pct}% custom staff/scholarship discount applied."

    frappe.msgprint(msg)

def update_student_fields(doc, method=None):
    if not doc.student:
        return

    if frappe.db.exists("Student", doc.student):
        frappe.db.set_value("Student", doc.student, {
            "custom_section": doc.student_category,
            "custom_form": doc.student_batch_name
        })
        frappe.msgprint(frappe._("Student {0} fields updated successfully.").format(doc.student))

def sync_old_student_rank_on_approval(doc, method=None):
    if doc.custom_application_type == "Old Student" and doc.custom_student_id:
        old_status = frappe.db.get_value("Student Applicant", doc.name, "application_status")
        
        if doc.application_status == "Approved" and old_status != "Approved":
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

def create_education_settings_custom_field():
    # Setup Sibling Ranking Toggle
    if not frappe.db.exists("Custom Field", {"dt": "Education Settings", "fieldname": "custom_use_sibling_ranking"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Education Settings",
            "fieldname": "custom_use_sibling_ranking",
            "label": "Use Sibling Ranking Matrix",
            "fieldtype": "Check",
            "insert_after": "user_creation_skip",
            "description": "Toggle ON for FWC style sibling ranking, toggle OFF for standard Form levels."
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    # Setup Punishment Logic Toggle
    if not frappe.db.exists("Custom Field", {"dt": "Education Settings", "fieldname": "custom_apply_attendance_punishment"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Education Settings",
            "fieldname": "custom_apply_attendance_punishment",
            "label": "Apply Punishment Hours to Standard Attendance",
            "fieldtype": "Check",
            "insert_after": "custom_use_sibling_ranking",
            "description": "Toggle ON to automatically compute punishment hours for standard Student Attendance records."
        }).insert(ignore_permissions=True)
        frappe.db.commit() 

# --- 3. REPORT CARD GENERATION TOOL MONKEY PATCH ---
import education.education.doctype.student_report_generation_tool.student_report_generation_tool as report_tool
from frappe.query_builder.functions import Count  # <-- Import Count directly from the source module

def patched_get_attendance_count(student, academic_year, academic_term=None):
    attendance = frappe._dict()
    attendance.total = 0
    attendance.present = 0
    attendance.absent = 0

    from_date, to_date = None, None

    if academic_year:
        from_date, to_date = frappe.db.get_value(
            "Academic Year", academic_year, ["year_start_date", "year_end_date"]
        )
    elif academic_term:
        from_date, to_date = frappe.db.get_value(
            "Academic Term", academic_term, ["term_start_date", "term_end_date"]
        )

    if from_date and to_date:
        SA = frappe.qb.DocType("Student Attendance")
        query = (
            frappe.qb.from_(SA)
            .select(SA.status, Count(SA.student).as_("count"))  # <-- Clean, explicit, and error-free
            .where(SA.student == student)
            .where(SA.docstatus == 1)
            .where(SA.date >= from_date)
            .where(SA.date <= to_date)
            .groupby(SA.status)
        )
        data = query.run(as_dict=True)

        for row in data:
            if row.status == "Present":
                attendance.present = row.count
            if row.status == "Absent":
                attendance.absent = row.count
            attendance.total += row.count
        return attendance
    else:
        frappe.throw("Please enter the Academic Year and set the Start and End date.")

# Safely exchange the reference pointers globally
report_tool.get_attendance_count = patched_get_attendance_count


@frappe.whitelist()
def update_student_overall_moua_total(student):
    if not student:
        return

    # 1. Sum up custom house/shift records
    taliui_total = frappe.db.sql("""
        SELECT SUM(houa_ngaue_moua) 
        FROM `tabTaliui Akonofo` 
        WHERE student = %s
    """, student)[0][0] or 0

    # 2. Sum up standard attendance records (if custom punishment field exists there)
    standard_total = 0
    if frappe.db.has_column("Student Attendance", "custom_houa_ngaue_moua"):
        standard_total = frappe.db.sql("""
            SELECT SUM(custom_houa_ngaue_moua) 
            FROM `tabStudent Attendance` 
            WHERE student = %s AND docstatus < 2
        """, student)[0][0] or 0

    # Combine totals safely
    grand_total = taliui_total + standard_total

    # Update Student Master DocType
    frappe.db.set_value("Student", student, "custom_total_moua", grand_total, update_modified=False)

def process_standard_attendance_punishment(doc, method=None):
    # Check if the global education settings toggle switch is turned ON
    apply_punishment = frappe.db.get_single_value("Education Settings", "custom_apply_attendance_punishment")
    
    if apply_punishment and doc.status == "Absent":
        doc.custom_houa_ngaue_moua = 2  # Matches your punishment_rate rules
    else:
        doc.custom_houa_ngaue_moua = 0

def trigger_standard_attendance_recalc(doc, method=None):
    # Trigger full calculation updates onto the master record
    update_student_overall_moua_total(doc.student)

# --- 4. PROGRAM ENROLLMENT TOOL MASSIVE IMPROVEMENT PATCH ---
from education.education.doctype.program_enrollment_tool.program_enrollment_tool import ProgramEnrollmentTool

def custom_get_students(self):
    students = []
    
    if not self.get_students_from:
        frappe.throw("Mandatory field - Get Students From")
    if not self.program:
        frappe.throw("Mandatory field - Program")
    if not self.academic_year:
        frappe.throw("Mandatory field - Academic Year")

    # CASE A: Pull clean newly accepted raw student applications
    if self.get_students_from == "Student Applicant":
        SA = frappe.qb.DocType("Student Applicant")
        students = (
            frappe.qb.from_(SA)
            .select(
                SA.name.as_("student_applicant"),
                SA.title.as_("student_name")
            )
            .where(SA.application_status == "Approved")
            .where(SA.program == self.program)
            .where(SA.academic_year == self.academic_year)
        ).run(as_dict=1)

    # CASE B: Smart filtering for returning / existing High School students
    elif self.get_students_from == "Program Enrollment":
        PE = frappe.qb.DocType("Program Enrollment")
        ST = frappe.qb.DocType("Student")
        
        # We need to find students whose PREVIOUS enrollment was active, 
        # but do not yet have an enrollment row for this TARGET new academic year run.
        previous_year = str(int(self.academic_year) - 1) if self.academic_year.isdigit() else None
        
        if previous_year:
            # Sub-query identifying who is already handled for the target year
            already_enrolled = (
                frappe.qb.from_(PE)
                .select(PE.student)
                .where(PE.academic_year == self.academic_year)
                .where(PE.docstatus < 2)
            )

            # Query picking up students from last year who need placement this year
            students = (
                frappe.qb.from_(PE)
                .join(ST).on(PE.student == ST.name)
                .select(
                    PE.student,
                    PE.student_name,
                    PE.student_batch_name,  # Last year's batch as a helper reference
                    PE.student_category     # Last year's section as a helper reference
                )
                .where(PE.academic_year == previous_year)
                .where(PE.docstatus < 2)
                .where(ST.enabled == 1)
                .where(PE.student.not_in(already_enrolled))
                .order_by(PE.student_batch_name, PE.student_name)
            ).run(as_dict=1)
        else:
            frappe.throw("Could not dynamically parse the previous Academic Year value to scan records.")

    if students:
        return students
    else:
        frappe.throw("No unallocated students found requiring setup parameters.")

def custom_enroll_students(self):
    from education.education.api import enroll_student
    total = len(self.students)
    
    for i, stud in enumerate(self.students):
        frappe.publish_realtime(
            "program_enrollment_tool", dict(progress=[i + 1, total]), user=frappe.session.user
        )
        
        # 1. Process Returning Students
        if stud.student:
            # Prevent double generation rows safely
            if frappe.db.exists("Program Enrollment", {"student": stud.student, "academic_year": self.new_academic_year, "docstatus": ["<", 2]}):
                continue
                
            pe = frappe.new_doc("Program Enrollment")
            pe.student = stud.student
            pe.student_name = stud.student_name
            pe.program = self.new_program
            pe.academic_year = self.new_academic_year
            pe.academic_term = self.new_academic_term
            pe.enrollment_date = self.enrollment_date
            
            # Row value takes complete priority, falls back to top-level default field if empty
            pe.student_batch_name = stud.student_batch_name if stud.student_batch_name else self.new_student_batch
            pe.student_category = stud.student_category if stud.student_category else self.new_student_category
            
            # Use submit() instead of save() to trigger invoice generation and tracking automation
            pe.insert(ignore_permissions=True)
            pe.submit()

        # 2. Process New Applicants
        elif stud.student_applicant:
            pe = enroll_student(stud.student_applicant)
            pe.academic_year = self.academic_year
            pe.academic_term = self.academic_term
            pe.enrollment_date = self.enrollment_date
            
            pe.student_batch_name = stud.student_batch_name if stud.student_batch_name else self.new_student_batch
            pe.student_category = stud.student_category if stud.student_category else self.new_student_category
            
            pe.save(ignore_permissions=True)
            pe.submit()

    frappe.msgprint(frappe._("Successfully created and processed structural updates for {0} Students.").format(total))

# 1. Apply the overrides to the Class fields
ProgramEnrollmentTool.get_students = custom_get_students
ProgramEnrollmentTool.enroll_students = custom_enroll_students

# 2. Force-inject them directly into Frappe's global whitelisted methods registry pool
frappe.whitelisted.add(ProgramEnrollmentTool.get_students)
frappe.whitelisted.add(ProgramEnrollmentTool.enroll_students)

# 3. Explicitly authorize HTTP POST requests for these two patched functions
# This satisfies the middleware handler checks and eliminates the KeyError completely.
if not hasattr(frappe, "allowed_http_methods_for_whitelisted_func"):
    frappe.allowed_http_methods_for_whitelisted_func = {}

frappe.allowed_http_methods_for_whitelisted_func[ProgramEnrollmentTool.get_students] = ["POST", "GET"]
frappe.allowed_http_methods_for_whitelisted_func[ProgramEnrollmentTool.enroll_students] = ["POST", "GET"]