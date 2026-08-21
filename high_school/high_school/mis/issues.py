import hashlib

import frappe

from frappe.utils import (
    cint,
    now_datetime,
)


CLOSED_STATUSES = {
    "Resolved",
    "Dismissed",
}


# =========================================================
# Issue Key
# =========================================================

def build_issue_key(
    source_type,
    reference_doctype=None,
    reference_name=None,
    school_term=None,
):
    """
    Build a deterministic key so the same underlying
    problem does not create duplicate MIS Issues.
    """

    raw = "|".join([
        source_type or "",
        reference_doctype or "",
        reference_name or "",
        school_term or "",
    ])

    digest = hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()

    prefix = (
        source_type
        or "MIS"
    )[:10].upper()

    return f"{prefix}-{digest}"


# =========================================================
# Serialize
# =========================================================

def serialize_issue(doc):
    """Return safe structured MIS Issue information."""

    return {
        "name":
            doc.name,

        "issue_key":
            doc.issue_key,

        "title":
            doc.title,

        "source_type":
            doc.source_type,

        "issue_type":
            doc.issue_type,

        "severity":
            doc.severity,

        "description":
            doc.description,

        "reference_doctype":
            doc.reference_doctype,

        "reference_name":
            doc.reference_name,

        "school_term":
            doc.school_term,

        "student":
            doc.student,

        "instructor":
            doc.instructor,

        "status":
            doc.status,

        "assigned_to":
            doc.assigned_to,

        "follow_up_date":
            str(doc.follow_up_date)
            if doc.follow_up_date
            else None,

        "resolution_type":
            doc.resolution_type,

        "resolution_notes":
            doc.resolution_notes,

        "exclude_from_kpis":
            bool(
                doc.exclude_from_kpis
            ),

        "resolved_by":
            doc.resolved_by,

        "resolved_on":
            str(doc.resolved_on)
            if doc.resolved_on
            else None,
    }


# =========================================================
# Create / Get Issue
# =========================================================

def create_or_get_issue(
    *,
    source_type,
    issue_type,
    title,
    severity="Warning",
    description=None,
    reference_doctype=None,
    reference_name=None,
    school_term=None,
    student=None,
    instructor=None,
):
    """
    Return an existing issue for the reference or
    create one when none exists.
    """

    issue_key = build_issue_key(
        source_type=source_type,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        school_term=school_term,
    )

    existing_name = frappe.db.get_value(
        "MIS Issue",
        {
            "issue_key":
                issue_key,
        },
        "name",
    )

    if existing_name:

        doc = frappe.get_doc(
            "MIS Issue",
            existing_name,
        )

        # Only refresh detection information while
        # the problem is still active.
        if doc.status not in CLOSED_STATUSES:

            doc.issue_type = (
                issue_type
            )

            doc.title = (
                title
            )

            doc.severity = (
                severity
            )

            doc.description = (
                description
            )

            doc.last_detected = (
                now_datetime()
            )

            if instructor:
                doc.instructor = instructor

            if student:
                doc.student = student

            doc.save()

        return serialize_issue(
            doc
        )

    doc = frappe.get_doc({
        "doctype":
            "MIS Issue",

        "issue_key":
            issue_key,

        "source_type":
            source_type,

        "issue_type":
            issue_type,

        "title":
            title,

        "severity":
            severity,

        "description":
            description,

        "reference_doctype":
            reference_doctype,

        "reference_name":
            reference_name,

        "school_term":
            school_term,

        "student":
            student,

        "instructor":
            instructor,

        "status":
            "Open",

        "first_detected":
            now_datetime(),

        "last_detected":
            now_datetime(),
    })

    doc.insert()

    return serialize_issue(
        doc
    )


# =========================================================
# Attendance Issue Map
# =========================================================

def get_course_attendance_issue_map(
    course_schedule_names,
    school_term=None,
):
    """
    Return MIS Issues linked to Course Schedules,
    indexed by Course Schedule name.
    """

    if not course_schedule_names:
        return {}

    filters = {
        "source_type":
            "Attendance",

        "reference_doctype":
            "Course Schedule",

        "reference_name": [
            "in",
            course_schedule_names,
        ],
    }

    if school_term:

        filters[
            "school_term"
        ] = school_term

    rows = frappe.get_all(
        "MIS Issue",
        filters=filters,
        fields=[
            "name",
            "issue_key",
            "title",
            "issue_type",
            "severity",

            "reference_name",

            "status",
            "assigned_to",
            "follow_up_date",

            "resolution_type",
            "resolution_notes",

            "exclude_from_kpis",

            "resolved_by",
            "resolved_on",
        ],
        order_by="modified desc",
    )

    output = {}

    for row in rows:

        # If duplicates somehow exist, use the
        # most recently modified one.
        if (
            row.reference_name
            not in output
        ):

            output[
                row.reference_name
            ] = {
                "name":
                    row.name,

                "issue_key":
                    row.issue_key,

                "title":
                    row.title,

                "issue_type":
                    row.issue_type,

                "severity":
                    row.severity,

                "status":
                    row.status,

                "assigned_to":
                    row.assigned_to,

                "follow_up_date":
                    (
                        str(
                            row.follow_up_date
                        )
                        if row.follow_up_date
                        else None
                    ),

                "resolution_type":
                    row.resolution_type,

                "resolution_notes":
                    row.resolution_notes,

                "exclude_from_kpis":
                    bool(
                        row.exclude_from_kpis
                    ),

                "resolved_by":
                    row.resolved_by,

                "resolved_on":
                    (
                        str(
                            row.resolved_on
                        )
                        if row.resolved_on
                        else None
                    ),
            }

    return output


# =========================================================
# Management Actions
# =========================================================

def mark_under_review(
    issue_name,
):
    """Move an MIS Issue into Under Review."""

    doc = frappe.get_doc(
        "MIS Issue",
        issue_name,
    )

    doc.check_permission(
        "write"
    )

    if doc.status in CLOSED_STATUSES:

        frappe.throw(
            "A resolved or dismissed issue must "
            "be reopened before it can be reviewed."
        )

    doc.status = (
        "Under Review"
    )

    doc.save()

    return serialize_issue(
        doc
    )


def resolve_issue(
    issue_name,
    resolution_type,
    resolution_notes=None,
    exclude_from_kpis=0,
):
    """
    Resolve an issue without changing the original
    attendance/assessment/finance records.
    """

    doc = frappe.get_doc(
        "MIS Issue",
        issue_name,
    )

    doc.check_permission(
        "write"
    )

    doc.status = (
        "Resolved"
    )

    doc.resolution_type = (
        resolution_type
    )

    doc.resolution_notes = (
        resolution_notes
    )

    doc.exclude_from_kpis = (
        cint(
            exclude_from_kpis
        )
    )

    doc.save()

    return serialize_issue(
        doc
    )


def reopen_issue(
    issue_name,
):
    """Reopen a previously resolved MIS Issue."""

    doc = frappe.get_doc(
        "MIS Issue",
        issue_name,
    )

    doc.check_permission(
        "write"
    )

    doc.status = (
        "Open"
    )

    doc.save()

    return serialize_issue(
        doc
    )