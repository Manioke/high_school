import re

import frappe
from frappe import _

from education.education.doctype.fee_schedule.fee_schedule import (
    create_sales_invoice,
)


def get_fee_structure_for_student(student, batch_name=None):
    """
    Determine the Fee Structure for the student.

    The Program Enrollment student_batch is preferred.
    Student.custom_form is only used as a fallback.

    Examples:
        N + F04 + C01 -> NF04C01
        N + TV + C01  -> NTVC01
    """

    student_doc = frappe.get_doc("Student", student)

    # Determine student stream/category.
    stream = (
        "I"
        if student_doc.custom_section == "INT"
        else "N"
    )

    # Prefer Program Enrollment.student_batch.
    batch_name = batch_name or student_doc.custom_form

    if not batch_name:
        frappe.throw(
            _(
                "Student {0} does not have a Student Batch/Form."
            ).format(student)
        )

    batch_name = str(batch_name)

    # TVET
    if "TVET" in batch_name.upper():
        form_code = "TV"

    # Normal Forms
    else:
        digits = re.findall(r"\d+", batch_name)

        if not digits:
            frappe.throw(
                _(
                    "Could not determine the student's form "
                    "from batch {0}."
                ).format(batch_name)
            )

        form_code = f"F0{digits[0]}"

    # Optional sibling ranking.
    use_sibling_rank = frappe.db.get_single_value(
        "Education Settings",
        "custom_use_sibling_ranking",
    )

    rank = ""

    if use_sibling_rank:
        rank = (
            frappe.db.get_value(
                "Student",
                student,
                "custom_sibling_rank",
            )
            or "C01"
        )

    return f"{stream}{form_code}{rank}"


def get_fee_schedules(fee_structure):
    """
    Get all submitted Fee Schedules belonging
    to the Fee Structure.

    Academic Term is deliberately not used here.
    """

    fee_schedules = frappe.get_all(
        "Fee Schedule",
        filters={
            "fee_structure": fee_structure,
            "docstatus": 1,
        },
        fields=[
            "name",
            "fee_structure",
        ],
        order_by="creation asc",
    )

    if not fee_schedules:
        frappe.throw(
            _(
                "No submitted Fee Schedule was found "
                "for Fee Structure {0}."
            ).format(fee_structure)
        )

    return fee_schedules


def apply_student_fee_discount(invoice_name, student):
    """
    Apply the student's custom fee discount.
    """

    discount_pct = frappe.db.get_value(
        "Student",
        student,
        "custom_fee_discount_percentage",
    )

    if not discount_pct:
        return None

    discount_pct = float(discount_pct)

    if discount_pct <= 0:
        return None

    discount_factor = discount_pct / 100.0

    invoice = frappe.get_doc(
        "Sales Invoice",
        invoice_name,
    )

    for item in invoice.items:
        item.discount_percentage = discount_pct
        item.amount = (
            item.rate
            * item.qty
            * (1 - discount_factor)
        )

    invoice.flags.ignore_validate_update_after_submit = True

    invoice.save(
        ignore_permissions=True,
    )

    return discount_pct


def generate_custom_fees(enrollment, method=None):
    """
    Generate Sales Invoice(s) when a Program Enrollment
    is submitted.

    Current behaviour:

        Program Enrollment
                ↓
        Student Batch
                ↓
        Fee Structure
                ↓
        All Fee Schedules
                ↓
        Sales Invoice(s)

    Academic Term is NOT required.

    If there is currently one Fee Schedule, one invoice
    will be created.

    If there are later four Fee Schedules, four invoices
    will be created.

    Future developers can extend this function with:
        - applicable terms
        - individual due dates
        - mid-term enrollment
        - pro-rata fees
        - overdue logic
    """

    if not enrollment.student:
        return None

    # ---------------------------------------------------------
    # 1. Determine Fee Structure
    # ---------------------------------------------------------

    fee_structure = get_fee_structure_for_student(
        student=enrollment.student,
        batch_name=enrollment.student_batch_name,
    )

    # ---------------------------------------------------------
    # 2. Get all Fee Schedules for that structure
    # ---------------------------------------------------------

    fee_schedules = get_fee_schedules(
        fee_structure
    )

    created_invoices = []

    # ---------------------------------------------------------
    # 3. Create one invoice per Fee Schedule
    # ---------------------------------------------------------

    for fee_schedule in fee_schedules:

        invoice_name = create_sales_invoice(
            fee_schedule.name,
            enrollment.student,
        )

        apply_student_fee_discount(
            invoice_name,
            enrollment.student,
        )

        created_invoices.append(invoice_name)

    # ---------------------------------------------------------
    # 4. Show result
    # ---------------------------------------------------------

    frappe.msgprint(
        _(
            "Created {0} Sales Invoice(s) for Fee Structure {1}."
        ).format(
            len(created_invoices),
            fee_structure,
        )
    )

    return created_invoices
