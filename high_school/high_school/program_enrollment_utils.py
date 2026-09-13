import random

import frappe
from frappe import _
from frappe.utils import today

from high_school.high_school.admissions import find_existing_student_for_applicant


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
        applicant_fields = _meta_fields("Student Applicant")
        fields = ["name as student_applicant"]
        name_field = "title" if "title" in applicant_fields else "student_name"
        fields.append(f"{name_field} as student_name")
        if "custom_student_batch_name" in applicant_fields:
            fields.append("custom_student_batch_name as student_batch_name")
        if "student_category" in applicant_fields:
            fields.append("student_category")
        students = frappe.get_all(
            "Student Applicant",
            filters={
                "application_status": "Approved",
                "program": tool.program,
                "academic_year": tool.academic_year,
            },
            fields=fields,
            order_by=f"{name_field} asc",
            limit_page_length=0,
        )

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
            .where(program_enrollment.program == tool.program)
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
            .where(program_enrollment.program == tool.program)
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

    _assign_tool_categories(tool)
    total = len(tool.students)
    target_program = tool.get("new_program") or tool.get("program")
    target_year = tool.get("new_academic_year") or tool.get("academic_year")
    target_term = tool.get("new_academic_term") or tool.get("academic_term")

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

        if student_row.get("student"):

            if frappe.db.exists(
                "Program Enrollment",
                {
                    "student": student_row.get("student"),
                    "program": target_program,
                    "academic_year": target_year,
                    "docstatus": ["<", 2],
                },
            ):
                continue

            enrollment = frappe.new_doc(
                "Program Enrollment"
            )

            enrollment.student = student_row.get("student")
            enrollment.student_name = student_row.get("student_name")
            enrollment.program = target_program
            enrollment.academic_year = target_year
            enrollment.academic_term = target_term
            enrollment.enrollment_date = tool.get("enrollment_date") or today()

            enrollment.student_batch_name = (
                student_row.get("student_batch_name")
                or tool.get("new_student_batch")
            )

            enrollment.student_category = (
                student_row.get("student_category")
                or tool.get("new_student_category")
            )

            enrollment.insert(
                ignore_permissions=True
            )

            enrollment.submit()

        # -------------------------------------------------------------------
        # NEW APPLICANT
        # -------------------------------------------------------------------

        elif student_row.get("student_applicant"):
            applicant_name = student_row.get("student_applicant")
            applicant = frappe.get_doc("Student Applicant", applicant_name)
            existing_student = find_existing_student_for_applicant(applicant)

            if existing_student:
                if not frappe.db.exists("Student", existing_student):
                    frappe.throw(
                        _("Returning Student {0} selected by Applicant {1} does not exist.").format(
                            existing_student, applicant_name
                        )
                    )
                enrollment = frappe.new_doc("Program Enrollment")
                enrollment.student = existing_student
                enrollment.student_name = frappe.db.get_value(
                    "Student", existing_student, "student_name"
                )
                frappe.db.set_value("Student", existing_student, "enabled", 1, update_modified=False)
            else:
                enrollment = enroll_student(applicant_name)

            enrollment.program = target_program
            enrollment.academic_year = target_year
            enrollment.academic_term = target_term
            enrollment.enrollment_date = tool.get("enrollment_date") or today()

            enrollment.student_batch_name = (
                student_row.get("student_batch_name")
                or applicant.get("custom_student_batch_name")
                or tool.get("new_student_batch")
            )

            enrollment.student_category = (
                student_row.get("student_category")
                or tool.get("new_student_category")
            )

            if enrollment.meta.has_field("custom_student_applicant"):
                enrollment.custom_student_applicant = applicant_name

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

    return {"processed": total}


@frappe.whitelist()
def get_program_enrollment_tool_students(
    get_students_from=None,
    program=None,
    academic_year=None,
    academic_term=None,
    **kwargs,
):
    """Compatibility endpoint for Education v16's module-level Get Students button."""
    frappe.only_for(["Education Manager", "Academics User", "System Manager"])
    tool = frappe._dict(
        get_students_from=get_students_from or "Student Applicant",
        program=program,
        academic_year=academic_year,
        academic_term=academic_term,
    )
    return get_program_enrollment_students(tool)


def _assign_tool_categories(tool):
    """Pre-allocate omitted categories so a bulk run reports every capacity failure."""
    pools = {}
    unassigned = []
    automatic = frappe.db.get_single_value(
        "School MIS Settings", "randomly_assign_student_category"
    )
    automatic = True if automatic is None else bool(int(automatic))
    if not automatic:
        return
    target_year = tool.get("new_academic_year") or tool.get("academic_year")
    target_program = tool.get("new_program") or tool.get("program")
    for row in tool.students:
        if row.get("student_category") or tool.get("new_student_category"):
            continue
        batch = row.get("student_batch_name") or tool.get("new_student_batch")
        if not batch:
            continue
        key = (target_year, target_program, batch)
        if key not in pools:
            probe = frappe._dict(academic_year=target_year, program=target_program, student_batch_name=batch)
            pool = []
            for group in _batch_groups(probe):
                maximum = int(group.get("max_strength") or 0)
                enrolled = _enrolled_category_count(probe, group.get("student_category"))
                active_members = frappe.db.count("Student Group Student", {"parent": group.name, "active": 1})
                used = max(enrolled, active_members)
                remaining = None if not maximum else max(maximum - used, 0)
                pool.append({"group": group.name, "category": group.get("student_category"), "remaining": remaining, "used": used})
            pools[key] = pool

        eligible = [item for item in pools[key] if item["remaining"] is None or item["remaining"] > 0]
        if not eligible:
            unassigned.append(row.get("student_name") or row.get("student") or row.get("student_applicant") or _("Unknown student"))
            continue
        lowest = min(item["used"] for item in eligible)
        chosen = random.SystemRandom().choice([item for item in eligible if item["used"] == lowest])
        row.student_category = chosen["category"]
        chosen["used"] += 1
        if chosen["remaining"] is not None:
            chosen["remaining"] -= 1

    if unassigned:
        frappe.throw(
            _("The following student(s) could not be assigned because all category groups in their selected batch are full:<br>{0}").format(
                "<br>".join(frappe.utils.escape_html(name) for name in unassigned)
            ),
            title=_("Student Group Capacity Reached"),
        )


def _meta_fields(doctype):
    return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _first_field(fields, *names):
    return next((name for name in names if name in fields), None)


def _batch_groups(doc):
    fields = _meta_fields("Student Group")
    batch_field = _first_field(fields, "student_batch_name", "student_batch", "batch")
    if not batch_field or "student_category" not in fields:
        frappe.throw(
            _("Student Group must expose Student Batch and Student Category fields before categories can be assigned automatically.")
        )

    filters = {batch_field: doc.student_batch_name, "academic_year": doc.academic_year}
    if doc.get("program") and "program" in fields:
        filters["program"] = doc.program
    if "disabled" in fields:
        filters["disabled"] = 0
    if "group_based_on" in fields:
        filters["group_based_on"] = "Batch"

    query_fields = ["name", "student_category"]
    if "max_strength" in fields:
        query_fields.append("max_strength")
    groups = frappe.get_all(
        "Student Group",
        filters=filters,
        fields=query_fields,
        order_by="name asc",
        limit_page_length=0,
    )
    category_keys = [group.get("student_category") or "" for group in groups]
    duplicates = sorted({key for key in category_keys if category_keys.count(key) > 1})
    if duplicates:
        labels = [_("blank Student Category") if not key else key for key in duplicates]
        frappe.throw(
            _("Student Groups for Program {0}, Batch {1}, and Academic Year {2} must each have a unique Student Category. Duplicate allocation key(s): {3}.").format(
                doc.get("program") or _("Not set"), doc.student_batch_name, doc.academic_year, ", ".join(labels)
            )
        )
    return groups


def _enrolled_category_count(doc, category):
    filters = {
        "academic_year": doc.academic_year,
        "student_batch_name": doc.student_batch_name,
        "docstatus": ["<", 2],
    }
    if doc.get("program"):
        filters["program"] = doc.program
    filters["student_category"] = category if category else ["is", "not set"]
    if doc.name and not doc.is_new():
        filters["name"] = ["!=", doc.name]
    return frappe.db.count("Program Enrollment", filters)


def _group_usage(doc, group):
    enrolled = _enrolled_category_count(doc, group.get("student_category"))
    active_members = frappe.db.count(
        "Student Group Student", {"parent": group.name, "active": 1}
    )
    return max(enrolled, active_members)


def _validate_group_capacity(doc, group):
    maximum = int(group.get("max_strength") or 0)
    used = _group_usage(doc, group)
    if maximum and used >= maximum:
        frappe.throw(
            _("Student Group {0} is full ({1} of {2}). Select another available group/category.").format(
                group.name, used, maximum
            ),
            title=_("Student Group Capacity Reached"),
        )


def assign_available_student_category(doc, method=None):
    """Assign an omitted enrolment category from the selected batch's main groups.

    Capacity is checked before submission.  The chosen category is restricted to
    categories already configured on Batch-based Student Groups; no unrelated
    Student Category can be selected.
    """
    if not doc.get("student_batch_name") or not doc.get("academic_year") or not doc.get("program"):
        frappe.throw(
            _("Program, Student Batch, and Academic Year are required before a Student Group can be assigned automatically."),
            title=_("Student Category Not Assigned"),
        )

    batch_program = frappe.db.get_value("Student Batch Name", doc.student_batch_name, "custom_program")
    if batch_program and batch_program != doc.program:
        frappe.throw(_("Student Batch {0} belongs to Program {1}, not {2}.").format(doc.student_batch_name, batch_program, doc.program))

    groups = _batch_groups(doc)
    if not groups:
        frappe.throw(
            _("No active Batch-based Student Group is configured for Program {0}, Batch {1}, in {2}.").format(
                doc.program, doc.student_batch_name, doc.academic_year
            ),
            title=_("Student Category Not Assigned"),
        )

    configured = {group.get("student_category") or "": group for group in groups}
    if doc.get("student_category"):
        if doc.student_category not in configured:
            frappe.throw(_("Student Category {0} is not configured for Program {1}, Batch {2}, in {3}.").format(
                doc.student_category, doc.program, doc.student_batch_name, doc.academic_year
            ))
        _validate_group_capacity(doc, configured[doc.student_category])
        return

    if len(groups) == 1:
        _validate_group_capacity(doc, groups[0])
        doc.student_category = groups[0].get("student_category")
        return

    automatic = frappe.db.get_single_value("School MIS Settings", "randomly_assign_student_category")
    automatic = True if automatic is None else bool(int(automatic))
    if not automatic:
        frappe.throw(
            _("Select a Student Category before submitting this Program Enrollment. Automatic group balancing is disabled in School MIS Settings."),
            title=_("Student Category Required"),
        )

    eligible = []
    full = []
    for group in groups:
        maximum = int(group.get("max_strength") or 0)
        used = _group_usage(doc, group)
        if maximum and used >= maximum:
            full.append({"group": group.name, "category": group.student_category, "used": used, "maximum": maximum})
        else:
            eligible.append((group, used))

    if not eligible:
        details = "<br>".join(
            _("{0} ({1}): {2} of {3}").format(row["group"], row["category"], row["used"], row["maximum"])
            for row in full
        )
        student = doc.get("student_name") or doc.get("student") or _("this student")
        frappe.throw(
            _("{0} could not be assigned because every category group for batch {1} is full.<br>{2}").format(
                student, doc.student_batch_name, details
            ),
            title=_("All Student Groups Are Full"),
        )

    lowest = min(item[1] for item in eligible)
    chosen = random.SystemRandom().choice([item[0] for item in eligible if item[1] == lowest])
    doc.student_category = chosen.get("student_category")
