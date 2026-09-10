from collections import Counter

import frappe
from frappe.utils import getdate


STANDARD_LEAVING_REASONS = (
    "Graduated / Completed School",
    "Transferred to Another School",
    "Relocation",
    "Financial Reasons",
    "Academic Reasons",
    "Health Reasons",
    "Family Reasons",
    "Disciplinary Dismissal",
    "Deceased",
    "Other",
)


def _academic_year(academic_year):
    return frappe.db.get_value(
        "Academic Year",
        academic_year,
        ["year_start_date", "year_end_date"],
        as_dict=True,
    )


def _table_columns(doctype):
    """Return real database columns, not fields that only exist in metadata."""
    return set(frappe.db.get_table_columns(doctype) or [])


def _student_is_inactive(row, student_columns, as_of=None):
    if "enabled" not in student_columns or row.get("enabled") != 0:
        return False
    leaving_date = row.get("date_of_leaving")
    return not leaving_date or not as_of or getdate(leaving_date) <= getdate(as_of)


def _enrolment_count(academic_year, as_of=None):
    if not academic_year or not frappe.db.exists("DocType", "Program Enrollment"):
        return None
    students = {
        student
        for student in frappe.get_all(
            "Program Enrollment",
            filters={"academic_year": academic_year, "docstatus": 1},
            pluck="student",
            limit_page_length=0,
        )
        if student
    }
    if not students:
        return 0

    as_of = getdate(as_of) if as_of else None
    student_columns = _table_columns("Student")
    fields = ["name"]
    if "enabled" in student_columns:
        fields.append("enabled")
    if "date_of_leaving" in student_columns:
        fields.append("date_of_leaving")
    rows = frappe.get_all(
        "Student",
        filters={"name": ["in", list(students)]},
        fields=fields,
        limit_page_length=0,
    )
    inactive = set()
    for row in rows:
        # Frappe Education v16 disables a Student through its Enabled checkbox;
        # Student does not have the workflow-style ``status`` database column.
        if _student_is_inactive(row, student_columns, as_of):
            inactive.add(row.name)
    return len(students - inactive)


def _previous_academic_year(academic_year):
    current = _academic_year(academic_year)
    if not current or not current.year_start_date:
        return None
    rows = frappe.get_all(
        "Academic Year",
        filters={"year_end_date": ["<", current.year_start_date]},
        fields=["name", "year_start_date", "year_end_date"],
        order_by="year_end_date desc",
        limit_page_length=1,
    )
    return rows[0] if rows else None


def _normalise_free_text_reason(reason):
    text = (reason or "").strip().lower()
    if not text:
        return None
    keyword_groups = (
        ("Graduated / Completed School", ("graduat", "completed school", "finished school")),
        ("Transferred to Another School", ("transfer", "another school", "changed school")),
        ("Relocation", ("relocat", "moved", "move away", "overseas")),
        ("Financial Reasons", ("financial", "fee", "afford", "money")),
        ("Academic Reasons", ("academic", "grades", "learning")),
        ("Health Reasons", ("health", "medical", "illness", "sick")),
        ("Family Reasons", ("family", "parent", "guardian")),
        ("Disciplinary Dismissal", ("disciplin", "dismiss", "expel")),
        ("Deceased", ("deceased", "died", "death")),
    )
    for category, keywords in keyword_groups:
        if any(keyword in text for keyword in keywords):
            return category
    return "Other"


def _departure_summary(academic_year, as_of):
    year = _academic_year(academic_year)
    student_columns = _table_columns("Student")
    if not year or not {"enabled", "date_of_leaving"}.issubset(student_columns):
        return {"available": False, "total": 0, "reasons": [], "missing_reason_count": 0}

    end_date = min(getdate(year.year_end_date), getdate(as_of))
    fields = ["name", "date_of_leaving"]
    if "reason_for_leaving" in student_columns:
        fields.append("reason_for_leaving")
    standard_field = "custom_standardized_leaving_reason"
    if standard_field in student_columns:
        fields.append(standard_field)
    rows = frappe.get_all(
        "Student",
        filters={
            "enabled": 0,
            "date_of_leaving": ["between", [year.year_start_date, end_date]],
        },
        fields=fields,
        limit_page_length=0,
    )

    reasons = Counter()
    missing = 0
    standardized = 0
    for row in rows:
        reason = row.get(standard_field)
        if reason in STANDARD_LEAVING_REASONS:
            standardized += 1
        else:
            reason = _normalise_free_text_reason(row.get("reason_for_leaving"))
        if reason:
            reasons[reason] += 1
        else:
            missing += 1

    return {
        "available": True,
        "total": len(rows),
        "standardized_count": standardized,
        "missing_reason_count": missing,
        "reasons": [
            {"reason": reason, "count": count}
            for reason, count in reasons.most_common()
        ],
    }


def get_school_outlook(term, data):
    """Build a conservative management outlook from recorded school evidence."""
    direction = data.get("direction") or {}
    finance = (data.get("finance") or {}).get("operations") or {}
    as_of = finance.get("as_of") or term.end_date
    previous_year = _previous_academic_year(term.academic_year)
    current_enrolment = _enrolment_count(term.academic_year, as_of)
    previous_enrolment = (
        _enrolment_count(previous_year.name, previous_year.year_end_date)
        if previous_year else None
    )
    departures = _departure_summary(term.academic_year, as_of)

    change = None
    change_rate = None
    scenario = None
    if current_enrolment is not None and previous_enrolment is not None:
        change = current_enrolment - previous_enrolment
        change_rate = round(change / previous_enrolment * 100, 1) if previous_enrolment else None
        scenario = max(0, current_enrolment + change)

    improving = [row for row in direction.get("indicators") or [] if row.get("direction") == "improving"]
    declining = [row for row in direction.get("indicators") or [] if row.get("direction") == "declining"]
    score = len(improving) - len(declining)
    risks = []
    opportunities = []
    actions = []

    for row in declining:
        risks.append("{0} declined by {1} percentage point(s) from the previous term.".format(
            row.get("label"), abs(float(row.get("change") or 0))
        ))
    for row in improving:
        opportunities.append("{0} improved by {1} percentage point(s) from the previous term.".format(
            row.get("label"), abs(float(row.get("change") or 0))
        ))
    if finance.get("available") and float(finance.get("operating_surplus") or 0) < 0:
        score -= 1
        risks.append("The selected term is operating at a deficit on posted General Ledger entries.")
        actions.append(
            "For the largest loss-making P&L categories, record the action to reduce cost or increase income, the person responsible, the target amount, and the date management will review progress."
        )
    if change is not None:
        if change < 0:
            score -= 1
            risks.append("Active recorded enrolment is down by {0} student(s) from {1}.".format(abs(change), previous_year.name))
            actions.append("Review recorded leaving reasons, transfers, admissions conversion, and retention by year level.")
        elif change > 0:
            score += 1
            opportunities.append("Active recorded enrolment is up by {0} student(s) from {1}.".format(change, previous_year.name))
            actions.append("Check staffing, classroom capacity, and fee-collection capacity before the next intake.")

    non_completion_departures = sum(
        row["count"] for row in departures.get("reasons") or []
        if row["reason"] not in {"Graduated / Completed School", "Deceased"}
    )
    if non_completion_departures:
        score -= 1
        risks.append("{0} non-completion student departure(s) are recorded in {1}.".format(non_completion_departures, term.academic_year))
    if departures.get("missing_reason_count"):
        actions.append("Complete the Standard Leaving Reason and Reason for Leaving for {0} leaver(s) with missing reasons.".format(departures["missing_reason_count"]))
    if declining:
        actions.append("Assign a responsible person and next review date for each declining term indicator.")
    if not actions:
        actions.append("Continue collecting complete term data and review the outlook at the next executive MIS meeting.")

    evidence_count = len([row for row in direction.get("indicators") or [] if row.get("direction") != "no_data"])
    if change is not None:
        evidence_count += 1
    if departures.get("total"):
        evidence_count += 1
    confidence = "Moderate" if evidence_count >= 3 else "Low"
    if evidence_count == 0:
        status, label = "no_data", "Insufficient Evidence"
    elif score > 0:
        status, label = "positive", "Positive Outlook"
    elif score < 0:
        status, label = "at_risk", "Outlook at Risk"
    else:
        status, label = "watch", "Watch Closely"

    return {
        "status": status,
        "label": label,
        "confidence": confidence,
        "summary": "This is a planning outlook based on recorded term trends, active enrolment, and student departures; it is not a guaranteed prediction.",
        "enrolment": {
            "academic_year": term.academic_year,
            "current": current_enrolment,
            "previous_academic_year": previous_year.name if previous_year else None,
            "previous": previous_enrolment,
            "change": change,
            "change_rate": change_rate,
            "next_year_scenario": scenario,
        },
        "departures": departures,
        "risks": risks,
        "opportunities": opportunities,
        "recommended_actions": actions,
        "limitations": "Leaving analysis includes Students marked Disabled whose Date of Leaving falls within the Academic Year. The standardized category is preferred; existing free-text reasons are mapped conservatively and should be reviewed by school management.",
    }
