import frappe

from frappe.model.naming import make_autoname


STUDENT_APPLICANT_SERIES = "EDU-APP-.YYYY.-.#####"


def ensure_unique_student_applicant_name(doc, method=None):
    """Advance past applicant names occupied by explicitly imported records."""
    if getattr(frappe.flags, "in_import", False):
        return

    for _attempt in range(100000):
        candidate = make_autoname(STUDENT_APPLICANT_SERIES)
        if not frappe.db.exists("Student Applicant", candidate):
            doc.name = candidate
            # before_insert runs before Frappe's normal set_new_name call.
            # Marking the name as set preserves the collision-free candidate.
            doc.flags.name_set = True
            return

    frappe.throw(
        "Could not find an unused Student Applicant number. "
        "Review the EDU-APP naming series counter."
    )
