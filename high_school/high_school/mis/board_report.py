import json

import frappe
from frappe import _
from frappe.utils import escape_html, now_datetime

from high_school.high_school.mis.executive import get_executive_summary


MANAGER_ROLES = ("Education Manager", "System Manager")


def _value(value, suffix="%"):
    return "N/A" if value is None else "{0}{1}".format(value, suffix)


def _money(value, currency):
    return "{0} {1:,.2f}".format(currency or "", float(value or 0)).strip()


def _recommendations(data):
    recommendations = []
    for indicator in (data.get("direction") or {}).get("indicators") or []:
        if indicator.get("direction") == "declining":
            recommendations.append(
                "Prioritise {0}: it declined by {1} percentage point(s) from the previous term.".format(
                    indicator.get("label"), abs(float(indicator.get("change") or 0))
                )
            )
    persistent = data.get("persistent_absence") or {}
    if persistent.get("unique_students_flagged"):
        recommendations.append(
            "Complete individual attendance interventions for {0} currently actionable student(s).".format(
                persistent["unique_students_flagged"]
            )
        )
    course = (data.get("attendance") or {}).get("course") or {}
    submission = course.get("submission") or {}
    unresolved = int(submission.get("actionable_missing_sessions") or 0) + int(submission.get("actionable_incomplete_sessions") or 0)
    if unresolved:
        recommendations.append(
            "Review {0} unresolved missing or incomplete class-attendance submission(s) by instructor.".format(unresolved)
        )
    academics = data.get("academics") or {}
    if not academics.get("cycle_count"):
        recommendations.append("Create the School Examination Cycle for this term before assessment preparation continues.")
    finance = data.get("finance") or {}
    if finance.get("status") == "warning":
        recommendations.append(
            "Follow up overdue student accounts and monitor collection against the {0}% target.".format(finance.get("target"))
        )
    return recommendations or ["Maintain current controls and continue monitoring the next School Term comparison."]


def _report_html(data):
    term = data["school_term"]
    direction = data.get("direction") or {}
    attendance = data.get("attendance") or {}
    daily = (attendance.get("daily") or {}).get("summary") or {}
    course = ((attendance.get("course") or {}).get("performance") or {}).get("summary") or {}
    academics = data.get("academics") or {}
    preparation = academics.get("preparation") or {}
    results = academics.get("result_submission") or {}
    performance = academics.get("performance") or {}
    finance = data.get("finance") or {}
    indicator_rows = "".join(
        "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>".format(
            escape_html(row.get("label")), _value(row.get("current")),
            _value(row.get("previous")), escape_html((row.get("direction") or "no data").title()),
        ) for row in direction.get("indicators") or []
    )
    recommendations = "".join("<li>{0}</li>".format(escape_html(item)) for item in _recommendations(data))
    return """
      <h2>{title}</h2><p><b>School Term:</b> {term} ({start} to {end})</p>
      <h3>Direction: {direction}</h3><p>{summary}</p>
      <table class="table table-bordered"><thead><tr><th>Measure</th><th>Current</th><th>Previous</th><th>Direction</th></tr></thead><tbody>{indicators}</tbody></table>
      <h3>Current Condition</h3>
      <table class="table table-bordered"><tbody>
       <tr><th>Daily attendance</th><td>{daily}</td><th>Course attendance</th><td>{course}</td></tr>
       <tr><th>Exam requirements ready</th><td>{exam}</td><th>Due results submitted</th><td>{results}</td></tr>
       <tr><th>School academic average</th><td>{average}</td><th>Actionable persistent absence</th><td>{absence}</td></tr>
       <tr><th>Fees invoiced</th><td>{invoiced}</td><th>Fees collected</th><td>{collected} ({collection})</td></tr>
       <tr><th>Outstanding / overdue</th><td colspan="3">{outstanding} outstanding; {overdue} overdue</td></tr>
      </tbody></table>
      <h3>Recommended Management Actions</h3><ol>{recommendations}</ol>
    """.format(
        title=escape_html("Executive MIS Board Summary: {0} - {1}".format(term["academic_year"], term["term"])),
        term=escape_html(term["name"]), start=escape_html(term["start_date"]), end=escape_html(term["end_date"]),
        direction=escape_html(direction.get("label") or "Not Enough History"),
        summary=escape_html("This snapshot compares the current School Term with the immediately preceding term wherever authoritative data exists."),
        indicators=indicator_rows or '<tr><td colspan="4">No comparable previous-term measures.</td></tr>',
        daily=_value(daily.get("attendance_rate")), course=_value(course.get("attendance_rate")),
        exam=_value(preparation.get("coverage_rate")), results=_value(results.get("submission_rate")),
        average=_value(performance.get("school_average")),
        absence=(data.get("persistent_absence") or {}).get("unique_students_flagged", 0),
        invoiced=_money(finance.get("invoiced"), finance.get("currency")),
        collected=_money(finance.get("collected"), finance.get("currency")), collection=_value(finance.get("collection_rate")),
        outstanding=_money(finance.get("outstanding"), finance.get("currency")), overdue=_money(finance.get("overdue"), finance.get("currency")),
        recommendations=recommendations,
    )


@frappe.whitelist()
def create_board_report(school_term):
    frappe.only_for(MANAGER_ROLES)
    data = get_executive_summary(school_term)
    if data.get("error"):
        frappe.throw(_(data["error"]))
    term = data["school_term"]
    direction = data.get("direction") or {}
    report = frappe.new_doc("Executive MIS Board Report")
    report.update({
        "report_title": "Executive MIS Board Summary: {0} - {1}".format(term["academic_year"], term["term"]),
        "school_term": term["name"], "academic_year": term["academic_year"],
        "previous_school_term": (direction.get("previous_term") or {}).get("name"),
        "generated_on": now_datetime(), "generated_by": frappe.session.user,
        "direction_status": direction.get("label") or "Not Enough History",
        "direction_summary": "Current term compared with the immediately preceding School Term using available authoritative measures.",
        "executive_summary": _report_html(data),
        "snapshot_json": json.dumps(data, default=str, indent=2),
    })
    report.insert()
    return {"name": report.name}
