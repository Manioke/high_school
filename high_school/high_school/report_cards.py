from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.pdf import get_pdf

from high_school.high_school.performance import generate_performance_summaries


REPORT_CARD_ROLES = ("Academics User", "Education Manager", "System Manager")


def _check_access():
    frappe.only_for(REPORT_CARD_ROLES)


def _meta_fields(doctype):
    return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _group_names(program, academic_year, student_batch):
    fields = _meta_fields("Student Group")
    filters = {"academic_year": academic_year}
    if "disabled" in fields:
        filters["disabled"] = 0
    if "group_based_on" in fields:
        filters["group_based_on"] = "Batch"
    if program and "program" in fields:
        filters["program"] = program
    batch_field = next(
        (name for name in ("student_batch", "student_batch_name", "batch") if name in fields),
        None,
    )
    if not batch_field:
        frappe.throw(_("This Education version does not expose a Student Batch field on Student Group."))
    filters[batch_field] = student_batch
    return frappe.get_all(
        "Student Group", filters=filters, pluck="name", order_by="name asc", limit_page_length=0
    )


def _periods(program, academic_year, school_term, student_batch):
    term_year = frappe.db.get_value("School Term", school_term, "academic_year")
    if term_year and term_year != academic_year:
        frappe.throw(_("School Term {0} does not belong to Academic Year {1}.").format(school_term, academic_year))
    groups = _group_names(program, academic_year, student_batch)
    if not groups:
        return []
    return frappe.get_all(
        "School Performance Period",
        filters={
            "academic_year": academic_year,
            "school_term": school_term,
            "main_student_group": ["in", groups],
        },
        fields=["name", "main_student_group"],
        order_by="main_student_group asc",
        limit_page_length=0,
    )


def _summaries(periods, include_incomplete=False, include_drafts=True):
    if not periods:
        return []
    filters = {
        "performance_period": ["in", [row.name for row in periods]],
        "docstatus": ["<", 2] if include_drafts else 1,
    }
    if not include_incomplete:
        filters["status"] = "Complete"
    return frappe.get_all(
        "Student Performance Summary",
        filters=filters,
        fields=[
            "name", "student", "student_name", "main_student_group",
            "performance_period", "status", "overall_percentage", "position",
            "rank_out_of", "docstatus",
        ],
        order_by="main_student_group asc, position asc, student_name asc",
        limit_page_length=0,
    )


@frappe.whitelist()
def get_report_card_preview(program, academic_year, school_term, student_batch, include_incomplete=0, include_drafts=1):
    _check_access()
    periods = _periods(program, academic_year, school_term, student_batch)
    summaries = _summaries(periods, cint(include_incomplete), cint(include_drafts))
    summary_by_period = {}
    for row in summaries:
        summary_by_period.setdefault(row.performance_period, []).append(row)
    rows = []
    for period in periods:
        values = summary_by_period.get(period.name, [])
        rows.append({
            "performance_period": period.name,
            "student_group": period.main_student_group,
            "report_cards": len(values),
            "complete": len([row for row in values if row.status == "Complete"]),
            "incomplete": len([row for row in values if row.status != "Complete"]),
            "submitted": len([row for row in values if row.docstatus == 1]),
            "draft": len([row for row in values if row.docstatus == 0]),
        })
    return {
        "rows": rows,
        "period_count": len(periods),
        "report_card_count": len(summaries),
        "message": (
            _("No School Performance Period matches these filters. Create the missing period first.")
            if not periods else
            _("{0} report card(s) found across {1} performance period(s).").format(len(summaries), len(periods))
        ),
    }


@frappe.whitelist()
def generate_batch_performance_summaries(program, academic_year, school_term, student_batch):
    _check_access()
    periods = _periods(program, academic_year, school_term, student_batch)
    if not periods:
        frappe.throw(_("No matching School Performance Period was found."))
    results = []
    for period in periods:
        try:
            outcome = generate_performance_summaries(period.name)
            results.append({"performance_period": period.name, "ok": True, **outcome})
        except Exception as exc:
            results.append({"performance_period": period.name, "ok": False, "error": str(exc)})
    return {"results": results, "success_count": len([row for row in results if row["ok"]])}


@frappe.whitelist()
def download_report_cards(program, academic_year, school_term, student_batch, include_incomplete=0, include_drafts=1, letter_head=None, print_format=None):
    _check_access()
    periods = _periods(program, academic_year, school_term, student_batch)
    summaries = _summaries(periods, cint(include_incomplete), cint(include_drafts))
    if not summaries:
        frappe.throw(_("No Student Performance Summaries match these filters."))
    if len(summaries) > 1000:
        frappe.throw(_("This selection contains more than 1,000 report cards. Choose a smaller Student Batch."))
    print_format = print_format or frappe.db.get_single_value(
        "School MIS Settings", "student_report_card_print_format"
    ) or "Student Performance Report Card"
    letter_head = letter_head or frappe.db.get_single_value(
        "School MIS Settings", "student_report_card_letter_head"
    )
    format_doctype = frappe.db.get_value("Print Format", print_format, "doc_type")
    if format_doctype != "Student Performance Summary":
        frappe.throw(_("Print Format {0} is not configured for Student Performance Summary.").format(print_format))

    pages = []
    for row in summaries:
        doc = frappe.get_doc("Student Performance Summary", row.name)
        doc.check_permission("print")
        pages.append(
            frappe.get_print(
                "Student Performance Summary",
                row.name,
                print_format=print_format,
                letterhead=letter_head or None,
                no_letterhead=0,
            )
        )
    html = '<div class="page-break"></div>'.join(pages)
    filename = "Report Cards - {0} - {1}.pdf".format(student_batch, school_term)
    frappe.local.response.filename = filename
    frappe.local.response.filecontent = get_pdf(html)
    frappe.local.response.type = "download"
