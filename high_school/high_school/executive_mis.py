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
    Public Executive MIS API endpoint.

    Business logic lives under:
    high_school.high_school.mis
    """

    return build_executive_summary(
        school_term=school_term
    )