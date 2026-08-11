import frappe
from frappe import _


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
# RETURNING STUDENT / SIBLING RANK
# ---------------------------------------------------------------------------

def sync_old_student_rank_on_approval(
    doc,
    method=None,
):
    """
    Synchronize sibling rank from an approved
    returning Student Applicant to the existing Student.
    """

    if (
        doc.custom_application_type != "Old Student"
        or not doc.custom_student_id
    ):
        return

    old_status = frappe.db.get_value(
        "Student Applicant",
        doc.name,
        "application_status",
    )

    if (
        doc.application_status == "Approved"
        and old_status != "Approved"
    ):
        frappe.db.set_value(
            "Student",
            doc.custom_student_id,
            "custom_sibling_rank",
            doc.custom_sibling_rank,
        )

        frappe.msgprint(
            _(
                "Master Student record updated with "
                "new Sibling Rank: {0}"
            ).format(
                doc.custom_sibling_rank
            )
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
