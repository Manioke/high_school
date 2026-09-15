"""Permission-filtered operational queue; no public endpoint or mass emailing."""
import frappe
from frappe.utils import nowdate
from high_school.high_school.mis.academic_explanations import PLAN_FIELDS, ACTION_FIELDS, follow_up, CLOSED
from collections import defaultdict


def execute(filters=None):
    filters = frappe._dict(filters or {})
    frappe.only_for(("Instructor", "Academics User", "Education Manager", "System Manager"))
    query = {}
    for field in ("school_term", "intervention_type", "assigned_to"):
        if filters.get(field):
            query[field] = filters[field]
    if not filters.get("include_closed"):
        query["status"] = ["not in", list(CLOSED)]
    # get_list applies the existing plan query permission and User Permissions.
    # Never replace this with get_all; action assignees can only see linked plans.
    plans = frappe.get_list("Student Intervention Plan", filters=query, fields=PLAN_FIELDS,
                           order_by="opened_on asc", limit_page_length=0)
    names = [p.name for p in plans]
    actions = frappe.get_all("Student Intervention Action", filters={
        "parent": ["in", names], "parenttype": "Student Intervention Plan", "parentfield": "actions",
    }, fields=ACTION_FIELDS, limit_page_length=0) if names else []
    grouped = defaultdict(list)
    for action in actions:
        grouped[action.parent].append(action)
    window = frappe.db.get_single_value("School MIS Settings", "intervention_follow_up_days")
    window = 21 if window is None else max(int(window), 0)
    data = []
    for plan in plans:
        state = follow_up(plan, grouped[plan.name], nowdate(), window)
        if filters.get("attention_only") and not state["gaps"]:
            continue
        data.append({
            "plan": plan.name, "student": plan.student, "course": plan.course,
            "plan_owner": plan.assigned_to, "status": plan.status,
            "root_cause": plan.root_cause if state["diagnosed"] else "Diagnosis not supported by notes",
            "days_open": state["days_open"], "next_due_date": state["next_due_date"],
            "overdue_actions": state["overdue_actions"],
            "overdue_owners": ", ".join(state["overdue_owners"]),
            "follow_up": "; ".join(state["gaps"]) or "No recording gap identified; review outcomes in the plan",
        })
    columns = [
        {"fieldname":"plan", "label":"Plan", "fieldtype":"Link", "options":"Student Intervention Plan", "width":180},
        {"fieldname":"student", "label":"Student", "fieldtype":"Link", "options":"Student", "width":140},
        {"fieldname":"course", "label":"Course", "fieldtype":"Link", "options":"Course", "width":150},
        {"fieldname":"plan_owner", "label":"Plan Owner", "fieldtype":"Link", "options":"User", "width":180},
        {"fieldname":"status", "label":"Status", "fieldtype":"Data", "width":130},
        {"fieldname":"root_cause", "label":"Recorded Diagnosis", "fieldtype":"Data", "width":200},
        {"fieldname":"days_open", "label":"Days Since Opened", "fieldtype":"Int", "width":100},
        {"fieldname":"next_due_date", "label":"Next Action Due", "fieldtype":"Date", "width":110},
        {"fieldname":"overdue_actions", "label":"Overdue Actions", "fieldtype":"Int", "width":100},
        {"fieldname":"overdue_owners", "label":"Overdue Action Owners", "fieldtype":"Data", "width":200},
        {"fieldname":"follow_up", "label":"Next Follow-up", "fieldtype":"Data", "width":420},
    ]
    return columns, data
