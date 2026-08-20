import frappe

from frappe.utils import (
    getdate,
    today,
)


def get_current_school_term():
    """
    Return the School Term containing today's date.
    """

    current_date = getdate(
        today()
    )

    terms = frappe.get_all(
        "School Term",

        filters={
            "start_date": [
                "<=",
                current_date,
            ],

            "end_date": [
                ">=",
                current_date,
            ],
        },

        fields=[
            "name",
            "academic_year",
            "term",
            "start_date",
            "end_date",
        ],

        order_by="start_date desc",

        limit=1,
    )

    return (
        terms[0]
        if terms
        else None
    )


def get_school_term(
    school_term=None,
):
    """
    Return the requested School Term.

    If one is not supplied, return the term
    containing today's date.
    """

    if school_term:

        return frappe.get_doc(
            "School Term",
            school_term,
        )

    return get_current_school_term()