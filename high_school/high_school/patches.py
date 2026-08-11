# api/patches.py
import frappe
import education.education.api
import education.education.doctype.student_report_generation_tool.student_report_generation_tool as report_tool
from education.education.doctype.program_enrollment_tool.program_enrollment_tool import ProgramEnrollmentTool

def apply_patches():
    # Attendance Patches
    education.education.api.make_attendance_records = custom_make_attendance_records
    education.education.api.mark_attendance = custom_mark_attendance
    
    # Report Tool Patch
    report_tool.get_attendance_count = patched_get_attendance_count
    
    # Program Enrollment Patch
    ProgramEnrollmentTool.get_students = custom_get_students
    ProgramEnrollmentTool.enroll_students = custom_enroll_students
    
    # Whitelist & HTTP registrations
    frappe.whitelisted.add(ProgramEnrollmentTool.get_students)
    frappe.whitelisted.add(ProgramEnrollmentTool.enroll_students)
    
    if not hasattr(frappe, "allowed_http_methods_for_whitelisted_func"):
        frappe.allowed_http_methods_for_whitelisted_func = {}
    
    frappe.allowed_http_methods_for_whitelisted_func[ProgramEnrollmentTool.get_students] = ["POST", "GET"]
    frappe.allowed_http_methods_for_whitelisted_func[ProgramEnrollmentTool.enroll_students] = ["POST", "GET"]