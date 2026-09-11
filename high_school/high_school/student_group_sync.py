"""Keep Student Group membership aligned with enrolment and Student choices."""

import frappe


def _group_filters(academic_year=None):
    fields = {field.fieldname for field in frappe.get_meta("Student Group").fields}
    filters = {}
    if academic_year and "academic_year" in fields:
        filters["academic_year"] = academic_year
    if "docstatus" in fields:
        filters["docstatus"] = ["<", 2]
    return filters


def _student_row_values(row, existing):
    student = row.get("student")
    return {
        "student": student,
        "student_name": row.get("student_name")
        or frappe.db.get_value("Student", student, "student_name"),
        "active": 1,
        "group_roll_number": existing.get(student, {}).get("group_roll_number"),
    }


def refresh_student_group(group_name):
    """Run the same membership calculation as Get Students for one group."""
    from high_school.high_school.api import get_students_custom

    group = frappe.get_doc("Student Group", group_name)
    rows = get_students_custom(
        student_group=group.name,
        student_group_name=group.get("student_group_name"),
        academic_year=group.get("academic_year"),
        group_based_on=group.get("group_based_on"),
        academic_term=group.get("academic_term"),
        program=group.get("program"),
        batch=group.get("batch") or group.get("student_batch_name") or group.get("student_batch"),
        student_category=group.get("student_category"),
        course=group.get("course"),
    ) or []

    candidate_students = list({row.get("student") for row in rows if row.get("student")})
    enabled_students = set()
    if candidate_students:
        enabled_students = {
            row.name
            for row in frappe.get_all(
                "Student",
                filters={"name": ["in", candidate_students], "enabled": 1},
                fields=["name"],
            )
        }
    existing = {row.student: row.as_dict() for row in group.get("students", []) if row.student}
    members = [
        _student_row_values(row, existing)
        for row in rows
        if row.get("student") in enabled_students and int(row.get("active", 1) or 0)
    ]
    members.sort(key=lambda row: (row.get("student_name") or "", row["student"]))

    old_members = [
        (row.student, int(row.active or 0), row.get("group_roll_number"))
        for row in group.get("students", [])
    ]
    new_members = [
        (row["student"], row["active"], row.get("group_roll_number")) for row in members
    ]
    if old_members == new_members:
        return False

    group.set("students", [])
    for member in members:
        group.append("students", member)
    group.flags.ignore_permissions = True
    group.save(ignore_permissions=True)
    return True


def refresh_all_student_groups(academic_year=None):
    """Reconcile every relevant Student Group and return a job summary."""
    checked = 0
    refreshed = 0
    failed = []
    for group_name in frappe.get_all(
        "Student Group",
        filters=_group_filters(academic_year),
        pluck="name",
        order_by="name asc",
        limit_page_length=0,
    ):
        checked += 1
        try:
            refreshed += int(refresh_student_group(group_name))
        except Exception:
            failed.append(group_name)
            frappe.log_error(
                title=f"Student Group refresh failed: {group_name}",
                message=frappe.get_traceback(),
            )
    return {"checked": checked, "refreshed": refreshed, "failed": failed}


def queue_student_group_refresh(academic_year=None):
    """Coalesce bulk-import events into one post-commit refresh per year."""
    suffix = str(academic_year or "all").replace(" ", "-")
    return frappe.enqueue(
        "high_school.high_school.student_group_sync.refresh_all_student_groups",
        academic_year=academic_year,
        queue="short",
        enqueue_after_commit=True,
        job_name=f"high-school-student-group-refresh-{suffix}",
    )


def refresh_groups_after_enrolment(doc, method=None):
    queue_student_group_refresh(doc.get("academic_year"))
