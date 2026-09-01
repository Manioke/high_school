from collections import defaultdict

import frappe

from frappe import _
from frappe.utils import escape_html

from high_school.high_school.mis.academic import (
    get_exam_preparation_summary,
    get_examination_cycles,
    get_result_submission_summary,
)
from high_school.high_school.mis.settings import get_mis_settings


MANAGER_ROLES = ("Education Manager", "System Manager")


def _add_item(grouped, user, item):
    if not user:
        return False
    grouped[user].append(item)
    return True


def _reminder_preview(school_term):
    settings = get_mis_settings()
    cycles = get_examination_cycles(school_term)
    preparation = get_exam_preparation_summary(
        school_term=school_term,
        cycles=cycles,
        settings=settings,
    )
    results = get_result_submission_summary(
        school_term=school_term,
        settings=settings,
    )

    grouped = defaultdict(list)
    no_recipient = 0

    for item in preparation.get("attention_items", []):
        user = item.get("lead_teacher_user") or item.get("hod_user")
        added = _add_item(
            grouped,
            user,
            {
                "area": "Exam Preparation",
                "course": item.get("course"),
                "group": item.get("student_batch"),
                "record": item.get("requirement"),
                "issues": ", ".join(item.get("attention_reasons") or []),
                "deadline": item.get("current_deadline"),
            },
        )
        no_recipient += int(not added)

    for item in results.get("attention_items", []):
        user = item.get("responsible_user") or item.get("hod_user")
        added = _add_item(
            grouped,
            user,
            {
                "area": "Assessment Results",
                "course": item.get("course"),
                "group": item.get("student_group"),
                "record": item.get("name"),
                "issues": item.get("attention_reason"),
                "deadline": item.get("result_due_date"),
            },
        )
        no_recipient += int(not added)

    recipients = []
    for user, items in sorted(grouped.items()):
        user_details = frappe.db.get_value(
            "User",
            user,
            ["email", "full_name", "enabled"],
            as_dict=True,
        )
        if not user_details or not user_details.enabled or not user_details.email:
            no_recipient += len(items)
            continue

        recipients.append(
            {
                "user": user,
                "email": user_details.email,
                "full_name": user_details.full_name or user,
                "item_count": len(items),
                "items": items,
            }
        )

    return {
        "school_term": school_term,
        "recipients": recipients,
        "recipient_count": len(recipients),
        "item_count": sum(row["item_count"] for row in recipients),
        "items_without_recipient": no_recipient,
    }


@frappe.whitelist()
def get_assessment_reminder_preview(school_term):
    frappe.only_for(MANAGER_ROLES)
    return _reminder_preview(school_term)


def _email_message(term_label, recipient):
    rows = []
    for item in recipient["items"]:
        rows.append(
            """
            <tr>
                <td>{area}</td>
                <td>{course}</td>
                <td>{group}</td>
                <td>{issues}</td>
                <td>{deadline}</td>
            </tr>
            """.format(
                area=escape_html(item.get("area") or ""),
                course=escape_html(item.get("course") or ""),
                group=escape_html(item.get("group") or ""),
                issues=escape_html(item.get("issues") or ""),
                deadline=escape_html(str(item.get("deadline") or "")),
            )
        )

    return """
        <p>Dear {name},</p>
        <p>The following assessment work for <strong>{term}</strong> requires your attention.</p>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr>
                    <th>Area</th>
                    <th>Course</th>
                    <th>Group / Batch</th>
                    <th>Required Action</th>
                    <th>Deadline</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        <p>Please complete or correct these items, then confirm their updated status in the school system.</p>
    """.format(
        name=escape_html(recipient["full_name"]),
        term=escape_html(term_label),
        rows="".join(rows),
    )


@frappe.whitelist()
def send_assessment_reminders(school_term, selected_users):
    frappe.only_for(MANAGER_ROLES)
    selected_users = set(frappe.parse_json(selected_users) or [])
    if not selected_users:
        frappe.throw(_("Select at least one teacher or HOD."))

    preview = _reminder_preview(school_term)
    allowed = {
        row["user"]: row
        for row in preview["recipients"]
    }
    invalid = selected_users - set(allowed)
    if invalid:
        frappe.throw(_("The recipient list is no longer current. Reload the preview."))

    term = frappe.db.get_value(
        "School Term",
        school_term,
        ["academic_year", "term"],
        as_dict=True,
    )
    if not term:
        frappe.throw(_("School Term {0} does not exist.").format(school_term))
    term_label = "{0} - {1}".format(term.academic_year, term.term)

    queued = []
    for user in sorted(selected_users):
        recipient = allowed[user]
        frappe.sendmail(
            recipients=[recipient["email"]],
            subject=_("Assessment work requiring attention: {0}").format(term_label),
            message=_email_message(term_label, recipient),
            reference_doctype="School Term",
            reference_name=school_term,
            now=False,
        )
        queued.append(
            {
                "user": user,
                "email": recipient["email"],
                "item_count": recipient["item_count"],
            }
        )

    return {
        "queued": queued,
        "recipient_count": len(queued),
        "item_count": sum(row["item_count"] for row in queued),
    }

