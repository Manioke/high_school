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

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

class HighSchoolLeaveApplication(StudentLeaveApplication):
    def on_submit(self):
        # This calls our custom logic below
        self.update_attendance()

    def update_attendance(self):
        # Get all groups the student belongs to
        student_groups = frappe.db.get_all(
            "Student Group Student",
            pluck="parent",
            filters={"student": self.student},
        )

        # Determine the primary group (for the daily/main record)
        primary_group = self.student_group or (student_groups[0] if student_groups else None)

        holiday_list = get_holiday_list()
        status = "Present" if self.mark_as_present else "Leave"

        # Loop through every day in the range
        for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
            date_str = dt.strftime("%Y-%m-%d")
            
            if is_holiday(holiday_list, date_str):
                continue

            # --- TRACK 1: MAIN DAILY RECORD ---
            # Creates/Updates the record for F5-A-2026 (No Schedule)
            if primary_group:
                self.force_attendance(date_str, status, primary_group, schedule_name=None)

            # --- TRACK 2: COURSE SCHEDULES ---
            # Find every lesson for THIS specific day for ALL groups the student is in
            if student_groups:
                schedules = frappe.db.get_all(
                    "Course Schedule",
                    filters={
                        "docstatus": 1,
                        "schedule_date": date_str,
                        "student_group": ["in", student_groups]
                    },
                    fields=["name", "student_group"]
                )

                for s in schedules:
                    # Creates/Updates the record for specific lessons like Economics
                    self.force_attendance(date_str, status, s.student_group, s.name)

    def force_attendance(self, date, status, group_name, schedule_name=None):
        # Define filter for searching existing records
        # If schedule_name is None, we look for records where course_schedule is empty
        cs_filter = schedule_name if schedule_name else ["in", ["", None]]
        
        existing = frappe.db.exists("Student Attendance", {
            "student": self.student,
            "date": date,
            "course_schedule": cs_filter,
            "docstatus": ["<", 2]
        })

        if existing:
            # Overwrite existing record (e.g., Change 'Absent' to 'Leave')
            frappe.db.set_value("Student Attendance", existing, {
                "status": status,
                "leave_application": self.name,
                "student_group": group_name
            })
            
            # Ensure it is submitted
            if frappe.db.get_value("Student Attendance", existing, "docstatus") == 0:
                frappe.db.set_value("Student Attendance", existing, "docstatus", 1)
        else:
            # Create a brand new record
            try:
                doc = frappe.new_doc("Student Attendance")
                doc.student = self.student
                doc.student_name = self.student_name
                doc.date = date
                doc.status = status
                doc.student_group = group_name
                doc.leave_application = self.name
                if schedule_name:
                    doc.course_schedule = schedule_name
                
                doc.insert(ignore_permissions=True, ignore_mandatory=True)
                doc.submit()
            except Exception:
                # Catch potential race conditions
                pass

def create_course_leave_attendance(doc, method):
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
        # Check if it's a holiday (optional, based on your settings)
        # if is_holiday(current_date): continue 

        # 3. Find all Course Schedules for this student's groups on this date
        schedules = frappe.get_all("Course Schedule",
            filters={
                "student_group": ["in", student_groups],
                "schedule_date": current_date
            },
            fields=["name", "student_group"]
        )

        for sch in schedules:
            # 4. Check if attendance already exists to avoid duplicates
            exists = frappe.db.exists("Student Attendance", {
                "student": doc.student,
                "course_schedule": sch.name,
                "date": current_date
            })

            if not exists:
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

        current_date = add_days(current_date, 1)