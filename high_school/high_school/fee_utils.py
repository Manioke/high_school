import re

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import getdate, nowdate, today

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


def _school_terms(academic_year):
    terms = frappe.get_all(
        "School Term",
        filters={"academic_year": academic_year},
        fields=["name", "term", "start_date", "end_date"],
        order_by="start_date asc, name asc",
        limit_page_length=0,
    )
    return [term for term in terms if term.start_date and term.end_date]


def resolve_enrollment_school_term(enrollment):
    terms = _school_terms(enrollment.academic_year)
    if not terms:
        frappe.throw(_("No dated School Terms are configured for Academic Year {0}.").format(enrollment.academic_year))
    enrollment_date = getdate(enrollment.get("enrollment_date") or today())
    containing = [term for term in terms if getdate(term.start_date) <= enrollment_date <= getdate(term.end_date)]
    if containing:
        return containing[0]
    upcoming = [term for term in terms if getdate(term.start_date) > enrollment_date]
    if upcoming:
        return upcoming[0]
    frappe.throw(_("Enrollment date {0} falls after the final School Term in {1}.").format(enrollment_date, enrollment.academic_year))


def set_enrollment_school_term(enrollment, method=None):
    if enrollment.meta.has_field("custom_school_term"):
        enrollment.custom_school_term = resolve_enrollment_school_term(enrollment).name


def validate_fee_schedule_school_term(doc, method=None):
    if not doc.get("custom_school_term"):
        frappe.throw(_("School Term is required. Academic Term is not used by this billing workflow."))
    term_year = frappe.db.get_value("School Term", doc.custom_school_term, "academic_year")
    if not term_year:
        frappe.throw(_("School Term {0} does not exist.").format(doc.custom_school_term))
    if term_year != doc.academic_year:
        frappe.throw(
            _("School Term {0} belongs to Academic Year {1}, not {2}.").format(
                doc.custom_school_term, term_year, doc.academic_year
            )
        )


def get_fee_schedules(fee_structure, enrollment):
    """
    Get all submitted Fee Schedules belonging
    to the Fee Structure.

    Academic Term is deliberately not used. Only the enrollment School Term
    and later School Terms are billed, preventing a Term 2 transfer from being
    invoiced for Term 1.
    """

    fee_schedules = frappe.get_all(
        "Fee Schedule",
        filters={
            "fee_structure": fee_structure,
            "program": enrollment.program,
            "academic_year": enrollment.academic_year,
            "docstatus": 1,
        },
        fields=[
            "name",
            "fee_structure",
            "program",
            "academic_year",
            "custom_school_term",
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

    missing = [row.name for row in fee_schedules if not row.get("custom_school_term")]
    if missing:
        frappe.throw(_("Set School Term on these submitted Fee Schedules before enrolling students: {0}.").format(", ".join(missing)))
    term_rows = {row.name: row for row in _school_terms(enrollment.academic_year)}
    current = resolve_enrollment_school_term(enrollment)
    applicable = []
    for schedule in fee_schedules:
        term = term_rows.get(schedule.custom_school_term)
        if not term:
            frappe.throw(_("Fee Schedule {0} uses a School Term outside Academic Year {1}.").format(schedule.name, enrollment.academic_year))
        if getdate(term.start_date) >= getdate(current.start_date):
            schedule.term_start_date = term.start_date
            applicable.append(schedule)
    if not applicable:
        frappe.throw(
            _("No Fee Schedule applies from enrollment School Term {0} onward.").format(current.name)
        )
    return sorted(applicable, key=lambda row: (getdate(row.term_start_date), row.name))


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

    Academic Term is not used. School Term determines which invoices are created.

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

    fee_schedules = get_fee_schedules(fee_structure, enrollment)

    created_invoices = []

    # ---------------------------------------------------------
    # 3. Create one invoice per Fee Schedule
    # ---------------------------------------------------------

    skipped_invoices = []
    for fee_schedule in fee_schedules:

        existing = frappe.db.exists(
            "Sales Invoice",
            {"fee_schedule": fee_schedule.name, "student": enrollment.student, "docstatus": ["<", 2]},
        )
        if existing:
            skipped_invoices.append(existing)
            continue

        invoice_name = create_sales_invoice(
            fee_schedule.name,
            enrollment.student,
        )

        invoice_updates = {"student": enrollment.student}
        if "custom_school_term" in {field.fieldname for field in frappe.get_meta("Sales Invoice").fields}:
            invoice_updates["custom_school_term"] = fee_schedule.custom_school_term
        frappe.db.set_value("Sales Invoice", invoice_name, invoice_updates, update_modified=False)

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
            "Created {0} Sales Invoice(s) and kept {1} existing invoice(s) for Fee Structure {2}."
        ).format(
            len(created_invoices),
            len(skipped_invoices),
            fee_structure,
        )
    )

    return created_invoices


def _upsert_custom_field(dt, fieldname, **values):
    name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, "name")
    if name:
        doc = frappe.get_doc("Custom Field", name)
        for key, value in values.items():
            doc.set(key, value)
        doc.save(ignore_permissions=True)
        return
    frappe.get_doc({"doctype": "Custom Field", "dt": dt, "fieldname": fieldname, "module": "High School", **values}).insert(ignore_permissions=True)


def setup_school_term_fee_fields():
    """Install School Term billing fields and repair safe legacy invoice links."""
    _upsert_custom_field(
        "Fee Schedule", "custom_school_term", label="School Term", fieldtype="Link",
        options="School Term", insert_after="academic_year", reqd=1, in_list_view=1, allow_on_submit=1,
        description="Controls which School Term this schedule bills. Academic Term is not used by the High School billing workflow.",
    )
    _upsert_custom_field(
        "Program Enrollment", "custom_school_term", label="Enrollment School Term", fieldtype="Link",
        options="School Term", insert_after="enrollment_date", read_only=1,
    )
    _upsert_custom_field(
        "Sales Invoice", "custom_school_term", label="School Term", fieldtype="Link",
        options="School Term", insert_after="fee_schedule", read_only=1, in_list_view=1,
    )
    make_property_setter("Fee Schedule", "academic_term", "hidden", 1, "Check", validate_fields_for_doctype=False)
    frappe.clear_cache(doctype="Fee Schedule")
    frappe.clear_cache(doctype="Sales Invoice")
    invoice_fields = {field.fieldname for field in frappe.get_meta("Sales Invoice").fields}
    if "student" in invoice_fields:
        students = frappe.get_all("Student", filters={"customer": ["is", "set"]}, fields=["name", "customer"], limit_page_length=0)
        by_customer = {}
        duplicates = set()
        for student in students:
            if student.customer in by_customer:
                duplicates.add(student.customer)
            else:
                by_customer[student.customer] = student.name
        for customer, student in by_customer.items():
            if customer in duplicates:
                continue
            frappe.db.sql(
                """UPDATE `tabSales Invoice` SET student = %s
                WHERE customer = %s AND COALESCE(student, '') = ''""",
                (student, customer),
            )
    if "custom_school_term" in invoice_fields:
        frappe.db.sql(
            """UPDATE `tabSales Invoice` si
            INNER JOIN `tabFee Schedule` fs ON fs.name = si.fee_schedule
            SET si.custom_school_term = fs.custom_school_term
            WHERE COALESCE(si.custom_school_term, '') = ''
              AND COALESCE(fs.custom_school_term, '') != ''"""
        )
    frappe.clear_cache(doctype="Fee Schedule")
    frappe.clear_cache(doctype="Sales Invoice")
    frappe.db.commit()


def create_late_registration_invoice_link_field():
    """Create the source-invoice marker used to prevent duplicate late fees."""
    if frappe.db.exists(
        "Custom Field",
        {"dt": "Sales Invoice", "fieldname": "custom_late_registration_source_invoice"},
    ):
        return
    frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": "Sales Invoice",
            "module": "High School",
            "fieldname": "custom_late_registration_source_invoice",
            "label": "Late Registration Source Invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "insert_after": "fee_schedule",
            "read_only": 1,
            "no_copy": 1,
            "description": "The overdue Term 1 invoice that caused this automatic late-registration charge.",
        }
    ).insert(ignore_permissions=True)
    frappe.db.commit()


def _term_one_invoice_names(item_identifier):
    item_fields = {field.fieldname for field in frappe.get_meta("Sales Invoice Item").fields}
    searchable = [field for field in ("item_code", "item_name") if field in item_fields]
    if not searchable:
        return []
    return list(
        {
            row.parent
            for row in frappe.get_all(
                "Sales Invoice Item",
                filters={"parenttype": "Sales Invoice"},
                or_filters={field: item_identifier for field in searchable},
                fields=["parent"],
                limit_page_length=0,
            )
        }
    )


def _student_for_fee_invoice(invoice):
    """Resolve an Education Student from either invoice link."""
    if invoice.get("student"):
        return invoice.student

    customer = invoice.get("customer")
    if not customer or not frappe.get_meta("Student").has_field("customer"):
        return None

    students = frappe.get_all(
        "Student",
        filters={"customer": customer},
        pluck="name",
        order_by="modified desc",
        limit_page_length=2,
    )
    # Do not guess if bad master data links one Customer to several Students.
    return students[0] if len(students) == 1 else None


def _create_late_registration_invoice(fee_structure, source_invoice, student):
    """Build the late charge directly from a submitted Fee Structure."""
    structure = frappe.get_doc("Fee Structure", fee_structure)
    if structure.docstatus != 1:
        frappe.throw(_("Late Registration Fee Structure {0} must be submitted.").format(fee_structure))
    if not structure.get("components"):
        frappe.throw(_("Late Registration Fee Structure {0} has no components.").format(fee_structure))

    customer = source_invoice.get("customer")
    if not customer:
        customer = frappe.db.get_value("Student", student, "customer")
    if not customer:
        # Use Education's supported Customer creation/linking behavior.
        from education.education.doctype.fee_schedule.fee_schedule import (
            get_customer_from_student,
        )

        customer = get_customer_from_student(student)

    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = customer
    invoice.company = structure.get("company") or source_invoice.get("company")
    invoice.posting_date = nowdate()
    invoice.due_date = nowdate()
    if invoice.meta.has_field("student"):
        invoice.student = student
    if structure.get("receivable_account"):
        invoice.debit_to = structure.receivable_account
    if invoice.meta.has_field("custom_late_registration_source_invoice"):
        invoice.custom_late_registration_source_invoice = source_invoice.name

    for component in structure.components:
        invoice.append(
            "items",
            {
                "item_code": component.item,
                "qty": 1,
                "rate": component.amount,
                "price_list_rate": component.amount,
                "discount_percentage": component.get("discount") or 0,
                "cost_center": structure.get("cost_center"),
            },
        )

    invoice.flags.ignore_permissions = True
    invoice.insert(ignore_permissions=True)
    if frappe.db.get_single_value("Education Settings", "auto_submit_sales_invoice"):
        invoice.submit()
    return invoice.name


def create_overdue_term_one_late_fees():
    """Daily, create one Late Registration invoice per overdue Term 1 invoice."""
    settings = frappe.get_single("School MIS Settings")
    if not settings.get("enable_automatic_late_registration_fees"):
        return {"created": [], "skipped": 0, "errors": []}

    fee_structure = settings.get("late_registration_fee_structure")
    item_identifier = settings.get("term_one_fee_item") or "Term 1"
    if not fee_structure:
        return {
            "created": [],
            "skipped": 0,
            "errors": [
                "Configure a submitted Late Registration Fee Structure in "
                "School MIS Settings before enabling this automation."
            ],
        }
    if not frappe.db.exists("Fee Structure", {"name": fee_structure, "docstatus": 1}):
        return {
            "created": [],
            "skipped": 0,
            "errors": [f"Submitted Fee Structure {fee_structure} does not exist."],
        }

    invoice_fields = {field.fieldname for field in frappe.get_meta("Sales Invoice").fields}
    required = {"outstanding_amount", "due_date"}
    if not required.issubset(invoice_fields):
        return {"created": [], "skipped": 0, "errors": ["Required invoice fields are unavailable."]}

    source_names = _term_one_invoice_names(item_identifier)
    if not source_names:
        return {"created": [], "skipped": 0, "errors": []}

    sources = frappe.get_all(
        "Sales Invoice",
        filters={
            "name": ["in", source_names],
            "docstatus": 1,
            "due_date": ["<", nowdate()],
            "outstanding_amount": [">", 0],
        },
        fields=[
            field
            for field in ("name", "student", "customer", "due_date")
            if field == "name" or field in invoice_fields
        ],
        order_by="due_date asc, name asc",
        limit_page_length=0,
    )
    created = []
    skipped = 0
    errors = []
    marker_available = "custom_late_registration_source_invoice" in invoice_fields
    if not marker_available:
        return {
            "created": [],
            "skipped": 0,
            "errors": ["Run bench migrate before enabling automatic late-registration fees."],
        }
    for row in sources:
        if frappe.db.exists(
            "Sales Invoice",
            {"custom_late_registration_source_invoice": row.name, "docstatus": ["<", 2]},
        ):
            skipped += 1
            continue
        try:
            source = frappe.get_doc("Sales Invoice", row.name)
            student = _student_for_fee_invoice(source)
            if not student:
                errors.append(
                    f"{row.name}: no unique Student is linked directly or through Customer {source.get('customer') or '(not set)'}."
                )
                continue
            invoice_name = _create_late_registration_invoice(
                fee_structure, source, student
            )
            created.append(invoice_name)
        except Exception:
            errors.append(row.name)
            frappe.log_error(
                title=f"Automatic late-registration fee failed for {row.name}",
                message=frappe.get_traceback(),
            )
    return {"created": created, "skipped": skipped, "errors": errors}
