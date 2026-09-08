import frappe

from high_school.high_school.mis.executive import (
    get_executive_summary
    as build_executive_summary,
)


@frappe.whitelist()
def get_executive_summary(
    school_term=None,
):
    """
    Role-protected Executive MIS API endpoint.

    Business logic lives under:
    high_school.high_school.mis
    """

    frappe.only_for(("Education Manager", "System Manager"))

    return build_executive_summary(
        school_term=school_term
    )
