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
from high_school.high_school.mis.school_term import get_school_term
from high_school.high_school.mis.course_attendance import (
    get_course_attendance_sessions,
)


MANAGER_ROLES = ("Education Manager", "System Manager")
CLOSED_ISSUE_STATUSES = {"Resolved", "Dismissed"}


def _instructor_recipient(instructor):
    fields = {field.fieldname for field in frappe.get_meta("Instructor").fields}
    wanted = [name for name in ("employee", "user_id", "instructor_name") if name in fields]
    if not wanted:
        return None
    row = frappe.db.get_value("Instructor", instructor, wanted, as_dict=True)
    if not row:
        return None

    user = row.get("user_id")
    if not user and row.get("employee"):
        user = frappe.db.get_value("Employee", row.employee, "user_id")
    if not user:
        return None
    details = frappe.db.get_value(
        "User", user, ["email", "full_name", "enabled"], as_dict=True
    )
    if not details or not details.enabled or not details.email:
        return None
    return {
        "user": user,
        "email": details.email,
        "full_name": details.full_name or row.get("instructor_name") or instructor,
    }


def _attendance_reminder_preview(school_term):
    settings = get_mis_settings()
    term = get_school_term(school_term)
    if not term:
        frappe.throw(_("School Term {0} does not exist.").format(school_term))
    sessions = get_course_attendance_sessions(
        start_date=term.start_date,
        end_date=term.end_date,
        coverage_target=settings["attendance_coverage_target"],
        school_term=term.name,
    )
    grouped = defaultdict(list)
    for session in sessions:
        if session.get("submission_status") not in {"missing", "incomplete"}:
            continue
        if (session.get("management_issue") or {}).get("status") in CLOSED_ISSUE_STATUSES:
            continue
        if session.get("instructor"):
            grouped[session["instructor"]].append(session)

    threshold = max(1, int(settings["missing_attendance_reminder_threshold"] or 10))
    recipients = []
    no_recipient = 0
    for instructor, items in sorted(grouped.items()):
        if len(items) < threshold:
            continue
        recipient = _instructor_recipient(instructor)
        if not recipient:
            no_recipient += 1
            continue
        recipients.append({
            **recipient,
            "instructor": instructor,
            "item_count": len(items),
            "missing_count": sum(row["submission_status"] == "missing" for row in items),
            "incomplete_count": sum(row["submission_status"] == "incomplete" for row in items),
        })

    return {
        "school_term": term.name,
        "threshold": threshold,
        "action": settings["attendance_reminder_action"],
        "recipients": recipients,
        "recipient_count": len(recipients),
        "items_without_recipient": no_recipient,
    }


@frappe.whitelist()
def get_attendance_reminder_preview(school_term):
    frappe.only_for(MANAGER_ROLES)
    return _attendance_reminder_preview(school_term)


def _attendance_email(term_label, recipient, action):
    meeting = action == "Request Office Meeting"
    request = (
        "Please come to the school office for a meeting so these classes can be reviewed."
        if meeting else
        "Please submit or correct the attendance for these classes as soon as possible."
    )
    return """
        <p>Dear {name},</p>
        <p>For <strong>{term}</strong>, {count} historical class(es) assigned to you have unresolved attendance: {missing} missing and {incomplete} incomplete.</p>
        <p>{request}</p>
        <p>Management can filter the Attendance Investigation by your name to review the affected classes with you.</p>
    """.format(
        name=escape_html(recipient["full_name"]), term=escape_html(term_label),
        count=recipient["item_count"], missing=recipient["missing_count"],
        incomplete=recipient["incomplete_count"], request=escape_html(request),
    )


@frappe.whitelist()
def send_attendance_reminders(school_term, selected_users):
    frappe.only_for(MANAGER_ROLES)
    selected_users = set(frappe.parse_json(selected_users) or [])
    if not selected_users:
        frappe.throw(_("Select at least one instructor."))
    preview = _attendance_reminder_preview(school_term)
    allowed = {row["user"]: row for row in preview["recipients"]}
    if selected_users - set(allowed):
        frappe.throw(_("The recipient list is no longer current. Reload the preview."))
    term = frappe.db.get_value(
        "School Term", school_term, ["academic_year", "term"], as_dict=True
    )
    term_label = "{0} - {1}".format(term.academic_year, term.term)
    queued = []
    for user in sorted(selected_users):
        recipient = allowed[user]
        action = preview["action"]
        subject = (
            _("Attendance review meeting requested: {0}")
            if action == "Request Office Meeting" else
            _("Attendance submissions requiring attention: {0}")
        ).format(term_label)
        frappe.sendmail(
            recipients=[recipient["email"]], subject=subject,
            message=_attendance_email(term_label, recipient, action),
            reference_doctype="School Term", reference_name=school_term, now=False,
        )
        queued.append({"user": user, "email": recipient["email"], "item_count": recipient["item_count"]})
    return {"queued": queued, "recipient_count": len(queued), "action": preview["action"]}


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
