import frappe
from frappe import _


def get_program_enrollment_students(tool):
    """
    Return students for the custom Program Enrollment Tool logic.
    """

    if not tool.get_students_from:
        frappe.throw(_("Mandatory field - Get Students From."))

    if not tool.program:
        frappe.throw(_("Mandatory field - Program."))

    if not tool.academic_year:
        frappe.throw(_("Mandatory field - Academic Year."))

    students = []

    # -----------------------------------------------------------------------
    # STUDENT APPLICANT
    # -----------------------------------------------------------------------

    if tool.get_students_from == "Student Applicant":

        student_applicant = frappe.qb.DocType(
            "Student Applicant"
        )

        students = (
            frappe.qb.from_(student_applicant)
            .select(
                student_applicant.name.as_("student_applicant"),
                student_applicant.title.as_("student_name"),
            )
            .where(
                student_applicant.application_status
                == "Approved"
            )
            .where(
                student_applicant.program
                == tool.program
            )
            .where(
                student_applicant.academic_year
                == tool.academic_year
            )
        ).run(as_dict=True)

    # -----------------------------------------------------------------------
    # PREVIOUS PROGRAM ENROLLMENT
    # -----------------------------------------------------------------------

    elif tool.get_students_from == "Program Enrollment":

        program_enrollment = frappe.qb.DocType(
            "Program Enrollment"
        )

        student = frappe.qb.DocType("Student")

        try:
            previous_year = str(
                int(tool.academic_year) - 1
            )
        except (TypeError, ValueError):
            frappe.throw(
                _(
                    "Could not determine the previous "
                    "Academic Year from {0}."
                ).format(tool.academic_year)
            )

        already_enrolled = (
            frappe.qb.from_(program_enrollment)
            .select(program_enrollment.student)
            .where(
                program_enrollment.academic_year
                == tool.academic_year
            )
            .where(
                program_enrollment.docstatus < 2
            )
        )

        students = (
            frappe.qb.from_(program_enrollment)
            .join(student)
            .on(
                program_enrollment.student
                == student.name
            )
            .select(
                program_enrollment.student,
                program_enrollment.student_name,
                program_enrollment.student_batch_name,
                program_enrollment.student_category,
            )
            .where(
                program_enrollment.academic_year
                == previous_year
            )
            .where(
                program_enrollment.docstatus < 2
            )
            .where(student.enabled == 1)
            .where(
                program_enrollment.student.not_in(
                    already_enrolled
                )
            )
            .order_by(
                program_enrollment.student_batch_name,
                program_enrollment.student_name,
            )
        ).run(as_dict=True)

    if not students:
        frappe.throw(
            _(
                "No unallocated students found "
                "requiring setup parameters."
            )
        )

    return students


def enroll_program_students(tool):
    """Enroll the students selected by Program Enrollment Tool."""

    from education.education.api import enroll_student

    total = len(tool.students)

    for index, student_row in enumerate(tool.students):

        frappe.publish_realtime(
            "program_enrollment_tool",
            {
                "progress": [
                    index + 1,
                    total,
                ]
            },
            user=frappe.session.user,
        )

        # -------------------------------------------------------------------
        # RETURNING STUDENT
        # -------------------------------------------------------------------

        if student_row.student:

            if frappe.db.exists(
                "Program Enrollment",
                {
                    "student": student_row.student,
                    "academic_year": tool.new_academic_year,
                    "docstatus": ["<", 2],
                },
            ):
                continue

            enrollment = frappe.new_doc(
                "Program Enrollment"
            )

            enrollment.student = student_row.student
            enrollment.student_name = student_row.student_name
            enrollment.program = tool.new_program
            enrollment.academic_year = tool.new_academic_year
            enrollment.academic_term = tool.new_academic_term
            enrollment.enrollment_date = tool.enrollment_date

            enrollment.student_batch_name = (
                student_row.student_batch_name
                or tool.new_student_batch
            )

            enrollment.student_category = (
                student_row.student_category
                or tool.new_student_category
            )

            enrollment.insert(
                ignore_permissions=True
            )

            enrollment.submit()

        # -------------------------------------------------------------------
        # NEW APPLICANT
        # -------------------------------------------------------------------

        elif student_row.student_applicant:

            enrollment = enroll_student(
                student_row.student_applicant
            )

            enrollment.academic_year = tool.academic_year
            enrollment.academic_term = tool.academic_term
            enrollment.enrollment_date = tool.enrollment_date

            enrollment.student_batch_name = (
                student_row.student_batch_name
                or tool.new_student_batch
            )

            enrollment.student_category = (
                student_row.student_category
                or tool.new_student_category
            )

            enrollment.save(
                ignore_permissions=True
            )

            enrollment.submit()

    frappe.msgprint(
        _(
            "Successfully created and processed "
            "updates for {0} students."
        ).format(total)
    )
