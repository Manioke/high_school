import frappe

from education.education.doctype.program_enrollment_tool.program_enrollment_tool import ProgramEnrollmentTool

from high_school.high_school.program_enrollment_utils import (
    enroll_program_students,
    get_program_enrollment_students,
)


class HighSchoolProgramEnrollmentTool(ProgramEnrollmentTool):
    """Program Enrollment Tool using approved applicants and High School allocation rules."""

    @frappe.whitelist()
    def get_students(self):
        students = get_program_enrollment_students(self)
        self.set("students", [])
        for student in students:
            self.append("students", student)
        return self.students

    @frappe.whitelist()
    def enroll_students(self):
        return enroll_program_students(self)
