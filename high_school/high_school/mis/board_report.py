import json

import frappe
from frappe import _
from frappe.utils import escape_html, now_datetime

from high_school.high_school.mis.executive import get_executive_summary
from high_school.high_school.mis.academic_explanations import render_explanations_html


MANAGER_ROLES = ("Academics User", "Education Manager", "System Manager")


def _value(value, suffix="%"):
    return "N/A" if value is None else "{0}{1}".format(value, suffix)


def _money(value, currency):
    return "{0} {1:,.2f}".format(currency or "", float(value or 0)).strip()


def _status(value):
    return escape_html((value or "no data").replace("_", " ").title())


def _profit_and_loss_rows(operations, currency):
    rows = []
    for item in operations.get("income_breakdown") or []:
        rows.append(
            "<tr><td>Income</td><td>{0}</td><td>{1}</td><td>{2}</td>"
            "<td class='text-right'>{3}</td></tr>".format(
                escape_html(item.get("category") or "Other"),
                escape_html(item.get("account") or ""),
                escape_html(item.get("cost_center") or ""),
                _money(item.get("amount"), currency),
            )
        )
    for item in operations.get("expense_breakdown") or []:
        rows.append(
            "<tr><td>Expense</td><td>{0}</td><td>{1}</td><td>{2}</td>"
            "<td class='text-right'>{3}</td></tr>".format(
                escape_html(item.get("category") or "Other"),
                escape_html(item.get("account") or ""),
                escape_html(item.get("cost_center") or ""),
                _money(item.get("amount"), currency),
            )
        )
    return "".join(rows)


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
    operations = finance.get("operations") or {}
    if operations.get("available"):
        if float(operations.get("operating_surplus") or 0) < 0:
            recommendations.append(
                "Review the term operating deficit of {0}; confirm funding from prior-term reserves and reduce or defer non-essential spending.".format(
                    _money(abs(float(operations.get("operating_surplus") or 0)), operations.get("currency"))
                )
            )
        budget = operations.get("budget") or {}
        if float(budget.get("utilisation_rate") or 0) > 100:
            recommendations.append(
                "Investigate budget overspend: actual expenditure exceeds the submitted budget by {0}.".format(
                    _money(abs(float(budget.get("remaining") or 0)), operations.get("currency"))
                )
            )
        payroll = operations.get("payroll") or {}
        if payroll.get("reconciliation_status") == "warning":
            recommendations.append(payroll.get("reconciliation_message"))
        if float(payroll.get("payroll_payable") or 0) > 0:
            recommendations.append(
                "Settle or reconcile the payroll payable balance of {0}.".format(
                    _money(payroll.get("payroll_payable"), operations.get("currency"))
                )
            )
        fund_requests = operations.get("fund_requests") or {}
        if int(fund_requests.get("open_count") or 0):
            recommendations.append(
                "Review {0} open School Fund Request(s) and document approval or disbursement decisions.".format(
                    fund_requests.get("open_count")
                )
            )
    interventions = data.get("interventions") or {}
    if int(interventions.get("overdue") or 0):
        recommendations.append(
            "Review and reassign {0} overdue or escalated Student Intervention Plan(s).".format(
                interventions.get("overdue")
            )
        )
    return recommendations or ["Maintain current controls and continue monitoring the next School Term comparison."]


def _report_html(data):
    term = data["school_term"]
    direction = data.get("direction") or {}
    attendance = data.get("attendance") or {}
    daily = (attendance.get("daily") or {}).get("summary") or {}
    course_data = attendance.get("course") or {}
    course = (course_data.get("performance") or {}).get("summary") or {}
    course_coverage = course_data.get("coverage") or {}
    attendance_submission = course_data.get("submission") or {}
    academics = data.get("academics") or {}
    preparation = academics.get("preparation") or {}
    plans = preparation.get("assessment_plans") or {}
    results = academics.get("result_submission") or {}
    performance = academics.get("performance") or {}
    settings = data.get("settings") or {}
    interventions = data.get("interventions") or {}
    academic_outcomes = interventions.get("academic_outcomes") or {}
    finance = data.get("finance") or {}
    operations = finance.get("operations") or {}
    operations_currency = operations.get("currency") or finance.get("currency")
    budget = operations.get("budget") or {}
    payroll = operations.get("payroll") or {}
    fund_requests = operations.get("fund_requests") or {}
    fiscal_profit_and_loss = operations.get("fiscal_profit_and_loss") or {}
    profit_and_loss_rows = _profit_and_loss_rows(
        operations, operations_currency
    )
    fiscal_profit_and_loss_rows = _profit_and_loss_rows(
        fiscal_profit_and_loss, operations_currency
    )
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
      <table class="table table-bordered"><thead><tr><th>Measure</th><th>Current</th><th>Target</th><th>Status / Context</th></tr></thead><tbody>
       <tr><td>Daily attendance</td><td>{daily}</td><td>{attendance_target}</td><td>{daily_status}</td></tr>
       <tr><td>Course attendance</td><td>{course}</td><td>{attendance_target}</td><td>{course_status}</td></tr>
       <tr><td>Course coverage</td><td>{course_coverage}</td><td>{coverage_target}</td><td>{coverage_status}</td></tr>
       <tr><td>Attendance submission</td><td>{attendance_submission}</td><td>{submission_target}</td><td>{submission_status}</td></tr>
       <tr><td>Exam requirements ready</td><td>{exam}</td><td>{exam_target}</td><td>{exam_status}</td></tr>
       <tr><td>Assessment plan coverage</td><td>{plan_coverage}</td><td>{plan_target}</td><td>{plan_status}</td></tr>
       <tr><td>Due results submitted</td><td>{results}</td><td>{results_target}</td><td>{results_status}</td></tr>
       <tr><td>School academic average</td><td>{average}</td><td>{academic_target}</td><td>{academic_status}</td></tr>
       <tr><td>Actionable persistent absence</td><td>{absence}</td><td>Below {absence_threshold} absence</td><td>Students requiring intervention</td></tr>
       <tr><td>Fee collection</td><td>{collection}</td><td>{collection_target}</td><td>{collected} of {invoiced}</td></tr>
       <tr><td>Overdue fees</td><td>{overdue_rate}</td><td>Maximum {overdue_target}</td><td>{outstanding} outstanding; {overdue} overdue</td></tr>
      </tbody></table>
      <h3>Student Intervention Management</h3>
      <table class="table table-bordered"><thead><tr><th>Active Academic</th><th>Active Attendance</th><th>Escalated</th><th>Students Improved Since Previous Term</th><th>Students Not Improved</th></tr></thead><tbody>
       <tr><td>{academic_interventions}</td><td>{attendance_interventions}</td><td>{overdue_interventions}</td><td>{improved_students}</td><td>{not_improved_students}</td></tr>
      </tbody></table>
      <p><b>Average overall change across evaluated students:</b> {academic_improvement}. Term 1 establishes the baseline; later terms are compared with the immediately preceding official Student Performance Summary.</p>
      {academic_explanations}
      <h3>Whole-School Finance</h3>
      <table class="table table-bordered"><tbody>
       <tr><th>Cash and bank</th><td>{cash}</td><th>Term income</th><td>{term_income}</td></tr>
       <tr><th>Term expenses</th><td>{term_expenses}</td><th>Operating result</th><td>{operating_result} ({operating_margin})</td></tr>
       <tr><th>Budget used</th><td>{budget_used} of {budget_total}</td><th>Budget remaining</th><td>{budget_remaining} ({budget_rate})</td></tr>
       <tr><th>Wage expense posted</th><td>{wages}</td><th>Submitted gross / net payroll</th><td>{payroll_gross} / {payroll_processed}</td></tr>
       <tr><th>Payroll-to-ledger difference</th><td>{payroll_difference}</td><th>Payroll payable</th><td>{payroll_payable}</td></tr>
       <tr><th>Open fund requests</th><td colspan="3">{fund_requests}</td></tr>
      </tbody></table>
      <h3>Term Collected Fees and Expenses</h3>
      <p>Term income is student fees collected from invoices assigned to {term}. Expenses are submitted General Ledger entries from {start} through {finance_as_of}, scoped to {finance_scope}.</p>
      <table class="table table-bordered">
       <thead><tr><th>Type</th><th>Category</th><th>Account</th><th>Cost Center</th><th>Amount</th></tr></thead>
       <tbody>{profit_and_loss_rows}</tbody>
       <tfoot>
        <tr><th colspan="4">Term Income</th><th>{term_income}</th></tr>
        <tr><th colspan="4">Term Expenses</th><th>{term_expenses}</th></tr>
        <tr><th colspan="4">Operating Result</th><th>{operating_result}</th></tr>
       </tfoot>
      </table>
      <h3>Fiscal Year Profit and Loss</h3>
      <p>{fiscal_year}: submitted General Ledger entries from {fiscal_start} through {finance_as_of}. This gives the board the wider financial position alongside the term-only view.</p>
      <table class="table table-bordered">
       <thead><tr><th>Type</th><th>Category</th><th>Account</th><th>Cost Center</th><th>Amount</th></tr></thead>
       <tbody>{fiscal_profit_and_loss_rows}</tbody>
       <tfoot>
        <tr><th colspan="4">Fiscal Year Income</th><th>{fiscal_income}</th></tr>
        <tr><th colspan="4">Fiscal Year Expenses</th><th>{fiscal_expenses}</th></tr>
        <tr><th colspan="4">Fiscal Year Net Result</th><th>{fiscal_result}</th></tr>
       </tfoot>
      </table>
      <h3>Recommended Management Actions</h3><ol>{recommendations}</ol>
    """.format(
        title=escape_html("Executive MIS Board Summary: {0} - {1}".format(term["academic_year"], term["term"])),
        term=escape_html(term["name"]), start=escape_html(term["start_date"]), end=escape_html(term["end_date"]),
        direction=escape_html(direction.get("label") or "Not Enough History"),
        summary=escape_html("This snapshot compares the current School Term with the immediately preceding term wherever authoritative data exists."),
        indicators=indicator_rows or '<tr><td colspan="4">No comparable previous-term measures.</td></tr>',
        daily=_value(daily.get("attendance_rate")), course=_value(course.get("attendance_rate")),
        attendance_target=_value(settings.get("attendance_target")),
        daily_status=_status(daily.get("status")),
        course_status=_status(course.get("status")),
        course_coverage=_value(course_coverage.get("coverage_rate")),
        coverage_target=_value(settings.get("attendance_coverage_target")),
        coverage_status=_status(course_coverage.get("status")),
        attendance_submission=_value(attendance_submission.get("compliance_rate")),
        submission_target=_value(settings.get("attendance_submission_target")),
        submission_status=_status(attendance_submission.get("status")),
        exam=_value(preparation.get("coverage_rate")), results=_value(results.get("submission_rate")),
        exam_target=_value(settings.get("exam_preparation_target")),
        exam_status=_status(preparation.get("status")),
        plan_coverage=_value(plans.get("coverage_rate")),
        plan_target=_value(settings.get("assessment_plan_coverage_target")),
        plan_status=_status(plans.get("status")),
        results_target=_value(settings.get("assessment_result_submission_target")),
        results_status=_status(results.get("status")),
        average=_value(performance.get("school_average")),
        academic_target=_value(settings.get("academic_performance_target")),
        academic_status=_status(
            "no_data" if performance.get("school_average") is None
            else "healthy" if float(performance.get("school_average")) >= float(settings.get("academic_performance_target") or 60)
            else "warning"
        ),
        absence=(data.get("persistent_absence") or {}).get("unique_students_flagged", 0),
        absence_threshold=_value(settings.get("persistent_absence_threshold")),
        invoiced=_money(finance.get("invoiced"), finance.get("currency")),
        collected=_money(finance.get("collected"), finance.get("currency")), collection=_value(finance.get("collection_rate")),
        collection_target=_value(settings.get("fee_collection_target")),
        overdue_rate=_value(finance.get("overdue_rate")),
        overdue_target=_value(settings.get("overdue_fee_target")),
        outstanding=_money(finance.get("outstanding"), finance.get("currency")), overdue=_money(finance.get("overdue"), finance.get("currency")),
        academic_interventions=int(interventions.get("academic_open") or 0),
        attendance_interventions=int(interventions.get("attendance_open") or 0),
        overdue_interventions=int(interventions.get("overdue") or 0),
        improved_students=int(academic_outcomes.get("improved_students") or 0),
        not_improved_students=int(academic_outcomes.get("not_improved_students") or 0),
        academic_improvement=_value(academic_outcomes.get("average_change"), " percentage points"),
        cash=_money(operations.get("cash_and_bank"), operations_currency),
        term_income=_money(operations.get("term_income"), operations_currency),
        term_expenses=_money(operations.get("term_expenses"), operations_currency),
        operating_result=_money(operations.get("operating_surplus"), operations_currency),
        operating_margin=_value(operations.get("operating_margin")),
        budget_used=_money(budget.get("used"), operations_currency),
        budget_total=_money(budget.get("budget_total"), operations_currency),
        budget_remaining=_money(budget.get("remaining"), operations_currency),
        budget_rate=_value(budget.get("utilisation_rate")),
        wages=_money(operations.get("wage_expense"), operations_currency),
        payroll_gross=_money(payroll.get("gross_pay"), operations_currency),
        payroll_processed=_money(payroll.get("net_pay"), operations_currency),
        payroll_difference=_money(payroll.get("gross_to_wage_gl_difference"), operations_currency),
        payroll_payable=_money(payroll.get("payroll_payable"), operations_currency),
        fund_requests="{0} ({1} outstanding)".format(
            fund_requests.get("open_count") or 0,
            _money(fund_requests.get("outstanding"), operations_currency),
        ),
        finance_as_of=escape_html(operations.get("as_of") or term["end_date"]),
        finance_scope=escape_html(operations.get("scope") or "Not configured"),
        profit_and_loss_rows=(
            profit_and_loss_rows
            or '<tr><td colspan="5">No matching term income or expense entries.</td></tr>'
        ),
        fiscal_year=escape_html(
            fiscal_profit_and_loss.get("fiscal_year") or "Fiscal Year"
        ),
        fiscal_start=escape_html(
            fiscal_profit_and_loss.get("start_date") or "N/A"
        ),
        fiscal_profit_and_loss_rows=(
            fiscal_profit_and_loss_rows
            or '<tr><td colspan="5">No matching fiscal-year income or expense entries.</td></tr>'
        ),
        fiscal_income=_money(
            fiscal_profit_and_loss.get("income"), operations_currency
        ),
        fiscal_expenses=_money(
            fiscal_profit_and_loss.get("expenses"), operations_currency
        ),
        fiscal_result=_money(
            fiscal_profit_and_loss.get("net_result"), operations_currency
        ),
        academic_explanations=render_explanations_html(data.get("academic_explanations"), include_people=True, expand_groups=True),
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
