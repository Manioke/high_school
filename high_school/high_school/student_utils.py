import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


# ---------------------------------------------------------------------------
# STUDENT FIELD SYNCHRONIZATION
# ---------------------------------------------------------------------------

def update_student_fields(doc, method=None):
    """Synchronize selected enrollment fields to Student."""

    if not doc.student:
        return

    if not frappe.db.exists(
        "Student",
        doc.student,
    ):
        return

    frappe.db.set_value(
        "Student",
        doc.student,
        {
            "custom_section": doc.student_category,
            "custom_form": doc.student_batch_name,
        },
    )


# ---------------------------------------------------------------------------
# EDUCATION SETTINGS CUSTOM FIELDS
# ---------------------------------------------------------------------------

def create_education_settings_custom_fields():
    """Create required custom Education Settings fields."""

    fields = [
        {
            "fieldname": "custom_use_sibling_ranking",
            "label": "Use Sibling Ranking Matrix",
            "fieldtype": "Check",
            "insert_after": "user_creation_skip",
            "description": (
                "Toggle ON for FWC style sibling ranking, "
                "toggle OFF for standard Form levels."
            ),
        },
        {
            "fieldname": "custom_apply_attendance_punishment",
            "label": "Apply Punishment Hours to Standard Attendance",
            "fieldtype": "Check",
            "insert_after": "custom_use_sibling_ranking",
            "description": (
                "Toggle ON to automatically compute punishment "
                "hours for standard Student Attendance records."
            ),
        },
    ]

    for field in fields:
        if frappe.db.exists(
            "Custom Field",
            {
                "dt": "Education Settings",
                "fieldname": field["fieldname"],
            },
        ):
            continue

        frappe.get_doc(
            {
                "doctype": "Custom Field",
                "dt": "Education Settings",
                **field,
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()


def make_student_email_optional():
    """Junior-school Student records must not require a personal email address."""
    fields = {field.fieldname for field in frappe.get_meta("Student").fields}
    for fieldname in ("student_email_id", "student_email"):
        if fieldname in fields:
            make_property_setter(
                "Student",
                fieldname,
                "reqd",
                0,
                "Check",
                validate_fields_for_doctype=False,
            )


def create_student_batch_program_field():
    """Keep reusable Student Batch names scoped to one Program in the core app."""
    filters = {"dt": "Student Batch Name", "fieldname": "custom_program"}
    name = frappe.db.get_value("Custom Field", filters, "name")
    values = {
        "module": "High School",
        "label": "Program",
        "fieldtype": "Link",
        "options": "Program",
        "insert_after": "batch_name",
        "reqd": 1,
        "allow_in_quick_entry": 1,
        "in_list_view": 1,
        "in_standard_filter": 1,
        "description": "Program that owns this reusable Form/Batch name.",
    }
    if name:
        field = frappe.get_doc("Custom Field", name)
        changed = False
        for key, value in values.items():
            if field.get(key) != value:
                field.set(key, value)
                changed = True
        if changed:
            field.save(ignore_permissions=True)
        return
    frappe.get_doc({"doctype": "Custom Field", **filters, **values}).insert(ignore_permissions=True)


def enforce_core_only_registration_boundary():
    """Disable legacy public intake safely when the optional add-on is absent.

    Existing applicant data is preserved. Only public Web Form publication and
    legacy add-on fields are disabled/hidden, avoiding destructive migrations.
    """
    if "high_school_online_registration" in frappe.get_installed_apps():
        return

    for name in frappe.get_all(
        "Web Form",
        filters={"doc_type": "Student Applicant"},
        pluck="name",
        limit_page_length=0,
    ):
        web_form = frappe.get_doc("Web Form", name)
        changed = False
        if web_form.meta.has_field("published") and web_form.get("published"):
            web_form.published = 0
            changed = True
        if web_form.meta.has_field("login_required") and not web_form.get("login_required"):
            web_form.login_required = 1
            changed = True
        if changed:
            web_form.save(ignore_permissions=True)

    legacy_fields = frappe.get_all(
        "Custom Field",
        filters={
            "dt": "Student Applicant",
            "module": ["in", ["High School", "High School Online Registration"]],
        },
        pluck="name",
        limit_page_length=0,
    )
    source_field = frappe.db.get_value(
        "Custom Field",
        {"dt": "Program Enrollment", "fieldname": "custom_student_applicant"},
        "name",
    )
    if source_field:
        legacy_fields.append(source_field)
    for name in legacy_fields:
        field = frappe.get_doc("Custom Field", name)
        field.hidden = 1
        field.reqd = 0
        field.mandatory_depends_on = None
        field.save(ignore_permissions=True)

    frappe.clear_cache(doctype="Student Applicant")
    frappe.clear_cache(doctype="Program Enrollment")


def create_student_leaving_fields():
    """Add a portable reporting category without destroying the existing notes."""

    if frappe.db.exists(
        "Custom Field",
        {
            "dt": "Student",
            "fieldname": "custom_standardized_leaving_reason",
        },
    ):
        return

    frappe.get_doc(
        {
            "doctype": "Custom Field",
            "dt": "Student",
            "module": "High School",
            "fieldname": "custom_standardized_leaving_reason",
            "label": "Standard Leaving Reason",
            "fieldtype": "Select",
            "insert_after": "reason_for_leaving",
            "depends_on": 'eval:doc.status == "Disabled"',
            "options": "\nGraduated / Completed School\nTransferred to Another School\nRelocation\nFinancial Reasons\nAcademic Reasons\nHealth Reasons\nFamily Reasons\nDisciplinary Dismissal\nDeceased\nOther",
            "description": (
                "Select one reporting category. Keep Reason for Leaving for "
                "specific notes and supporting details."
            ),
        }
    ).insert(ignore_permissions=True)

    frappe.db.commit()
