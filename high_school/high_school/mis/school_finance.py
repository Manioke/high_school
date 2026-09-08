import frappe

from frappe.utils import flt, getdate, nowdate


OPEN_FUND_REQUEST_STATUSES = {
    "Draft",
    "Submitted",
    "Under Review",
    "Approved",
    "Partly Disbursed",
}


def _percentage(numerator, denominator):
    if not denominator:
        return None
    return round((flt(numerator) / flt(denominator)) * 100, 1)


def _doctype_exists(doctype):
    return bool(frappe.db.exists("DocType", doctype))


def _meta_fields(doctype):
    if not _doctype_exists(doctype):
        return set()
    return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _company(settings):
    return (
        settings.get("finance_company")
        or frappe.defaults.get_global_default("company")
    )


def _leaf_accounts(company, root_type=None, account_types=None):
    filters = {"company": company, "is_group": 0, "disabled": 0}
    if root_type:
        filters["root_type"] = root_type
    if account_types:
        filters["account_type"] = ["in", list(account_types)]
    return frappe.get_all("Account", filters=filters, pluck="name")


def _account_and_descendants(account, company):
    if not account:
        return []
    node = frappe.db.get_value(
        "Account",
        account,
        ["company", "lft", "rgt", "is_group"],
        as_dict=True,
    )
    if not node or node.company != company:
        return []
    if not node.is_group:
        return [account]
    return frappe.get_all(
        "Account",
        filters={
            "company": company,
            "is_group": 0,
            "lft": [">", node.lft],
            "rgt": ["<", node.rgt],
        },
        pluck="name",
    )


def _sum_gl(company, accounts, start_date=None, end_date=None, cost_center=None):
    if not accounts:
        return {"debit": 0.0, "credit": 0.0}

    filters = {
        "company": company,
        "account": ["in", list(set(accounts))],
    }
    if "is_cancelled" in _meta_fields("GL Entry"):
        filters["is_cancelled"] = 0
    if start_date and end_date:
        filters["posting_date"] = ["between", [start_date, end_date]]
    elif end_date:
        filters["posting_date"] = ["<=", end_date]
    if cost_center and "cost_center" in _meta_fields("GL Entry"):
        filters["cost_center"] = cost_center

    rows = frappe.get_all(
        "GL Entry",
        filters=filters,
        fields=[
            {"SUM": "debit", "as": "debit"},
            {"SUM": "credit", "as": "credit"},
        ],
    )
    row = rows[0] if rows else {}
    return {
        "debit": flt(row.get("debit")),
        "credit": flt(row.get("credit")),
    }


def _fiscal_year(as_of):
    rows = frappe.get_all(
        "Fiscal Year",
        filters={
            "year_start_date": ["<=", as_of],
            "year_end_date": [">=", as_of],
            "disabled": 0,
        },
        fields=["name", "year_start_date", "year_end_date"],
        order_by="year_start_date desc",
        limit_page_length=1,
    )
    return rows[0] if rows else None


def _budget_summary(company, as_of, cost_center):
    empty = {
        "available": _doctype_exists("Budget"),
        "status": "no_data",
        "fiscal_year": None,
        "budget_count": 0,
        "budget_total": 0.0,
        "used": 0.0,
        "remaining": 0.0,
        "utilisation_rate": None,
    }
    if not empty["available"] or not _doctype_exists("Fiscal Year"):
        return empty

    fiscal_year = _fiscal_year(as_of)
    if not fiscal_year:
        return empty
    empty["fiscal_year"] = fiscal_year.name

    budget_fields = _meta_fields("Budget")
    budget_filters = {"company": company, "docstatus": 1}
    if "fiscal_year" in budget_fields:
        budget_filters["fiscal_year"] = fiscal_year.name
    budget_rows = frappe.get_all(
        "Budget", filters=budget_filters, pluck="name"
    )

    budget_total = 0.0
    budget_accounts = set()
    included = []
    for name in budget_rows:
        budget = frappe.get_doc("Budget", name)
        if "fiscal_year" not in budget_fields:
            from_year = budget.get("from_fiscal_year")
            to_year = budget.get("to_fiscal_year")
            if from_year or to_year:
                from_start = frappe.db.get_value(
                    "Fiscal Year", from_year or to_year, "year_start_date"
                )
                to_end = frappe.db.get_value(
                    "Fiscal Year", to_year or from_year, "year_end_date"
                )
                if (
                    not from_start
                    or not to_end
                    or getdate(as_of) < getdate(from_start)
                    or getdate(as_of) > getdate(to_end)
                ):
                    continue
        if cost_center and budget.get("budget_against") == "Cost Center":
            if budget.get("cost_center") != cost_center:
                continue
        included.append(name)
        account_rows = budget.get("accounts") or []
        if not account_rows and budget.get("account"):
            account_rows = [
                {
                    "account": budget.get("account"),
                    "budget_amount": budget.get("budget_amount"),
                }
            ]
        for row in account_rows:
            budget_total += max(0, flt(row.get("budget_amount")))
            budget_accounts.update(
                _account_and_descendants(row.get("account"), company)
            )

    if not included:
        return empty

    totals = _sum_gl(
        company,
        budget_accounts,
        fiscal_year.year_start_date,
        min(getdate(as_of), getdate(fiscal_year.year_end_date)),
        cost_center,
    )
    used = max(0, totals["debit"] - totals["credit"])
    utilisation = _percentage(used, budget_total)
    return {
        "available": True,
        "status": "warning" if utilisation is not None and utilisation > 100 else "healthy",
        "fiscal_year": fiscal_year.name,
        "budget_count": len(included),
        "budget_total": round(budget_total, 2),
        "used": round(used, 2),
        "remaining": round(budget_total - used, 2),
        "utilisation_rate": utilisation,
    }


def _fund_request_summary(term, company, cost_center):
    empty = {
        "available": _doctype_exists("School Fund Request"),
        "request_count": 0,
        "open_count": 0,
        "requested": 0.0,
        "approved": 0.0,
        "disbursed": 0.0,
        "outstanding": 0.0,
        "items": [],
    }
    if not empty["available"]:
        return empty

    filters = {
        "company": company,
        "request_date": ["between", [term.start_date, term.end_date]],
    }
    if cost_center:
        filters["cost_center"] = cost_center
    rows = frappe.get_all(
        "School Fund Request",
        filters=filters,
        fields=[
            "name",
            "request_date",
            "requested_by",
            "purpose",
            "status",
            "requested_amount",
            "approved_amount",
            "disbursed_amount",
            "outstanding_amount",
            "progress",
            "required_by",
        ],
        order_by="request_date desc, modified desc",
        limit_page_length=50,
    )
    for row in rows:
        empty["requested"] += flt(row.requested_amount)
        empty["approved"] += flt(row.approved_amount)
        empty["disbursed"] += flt(row.disbursed_amount)
        empty["outstanding"] += flt(row.outstanding_amount)
        if row.status in OPEN_FUND_REQUEST_STATUSES:
            empty["open_count"] += 1
    empty["request_count"] = len(rows)
    empty["items"] = rows
    for key in ("requested", "approved", "disbursed", "outstanding"):
        empty[key] = round(empty[key], 2)
    return empty


def _payroll_summary(term, settings, company, cost_center, as_of):
    enabled = bool(settings.get("track_hr_payroll"))
    available = _doctype_exists("Salary Slip") and _doctype_exists(
        "Payroll Entry"
    )
    empty = {
        "enabled": enabled,
        "available": available,
        "status": "disabled" if not enabled else "no_data",
        "salary_slip_count": 0,
        "employee_count": 0,
        "gross_pay": 0.0,
        "deductions": 0.0,
        "net_pay": 0.0,
        "employer_contributions": 0.0,
        "payroll_payable": None,
        "payroll_payable_account_configured": bool(
            settings.get("payroll_payable_account")
        ),
        "payroll_payable_available": False,
        "payroll_entries": [],
    }
    if not enabled or not available:
        return empty

    slip_fields = _meta_fields("Salary Slip")
    slip_filters = {"company": company, "docstatus": 1}
    if "start_date" in slip_fields and "end_date" in slip_fields:
        slip_filters["start_date"] = ["<=", term.end_date]
        slip_filters["end_date"] = [">=", term.start_date]
    if cost_center and "cost_center" in slip_fields:
        slip_filters["cost_center"] = cost_center
    wanted_slip_fields = [
        "name",
        "employee",
        "gross_pay",
        "net_pay",
        "total_deduction",
        "total_employer_contribution",
    ]
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=slip_filters,
        fields=[
            field
            for field in wanted_slip_fields
            if field == "name" or field in slip_fields
        ],
        limit_page_length=0,
    )

    employees = set()
    for slip in salary_slips:
        if slip.get("employee"):
            employees.add(slip.employee)
        empty["gross_pay"] += flt(slip.get("gross_pay"))
        empty["deductions"] += flt(slip.get("total_deduction"))
        empty["net_pay"] += flt(slip.get("net_pay"))
        empty["employer_contributions"] += flt(
            slip.get("total_employer_contribution")
        )

    entry_fields = _meta_fields("Payroll Entry")
    entry_filters = {"company": company, "docstatus": ["<", 2]}
    if "start_date" in entry_fields and "end_date" in entry_fields:
        entry_filters["start_date"] = ["<=", term.end_date]
        entry_filters["end_date"] = [">=", term.start_date]
    if cost_center and "cost_center" in entry_fields:
        entry_filters["cost_center"] = cost_center
    wanted_entry_fields = [
        "name",
        "posting_date",
        "start_date",
        "end_date",
        "payroll_frequency",
        "status",
        "docstatus",
        "number_of_employees",
    ]
    payroll_entries = frappe.get_all(
        "Payroll Entry",
        filters=entry_filters,
        fields=[
            field
            for field in wanted_entry_fields
            if field == "name" or field in entry_fields
        ],
        order_by="start_date desc, modified desc",
        limit_page_length=50,
    )

    payable_account = settings.get("payroll_payable_account")
    payable_accounts = _account_and_descendants(payable_account, company)
    if payable_accounts:
        empty["payroll_payable_available"] = True
        payable_gl = _sum_gl(company, payable_accounts, end_date=as_of)
        empty["payroll_payable"] = round(
            payable_gl["credit"] - payable_gl["debit"], 2
        )

    empty.update(
        {
            "status": "healthy" if salary_slips else "no_data",
            "salary_slip_count": len(salary_slips),
            "employee_count": len(employees),
            "gross_pay": round(empty["gross_pay"], 2),
            "deductions": round(empty["deductions"], 2),
            "net_pay": round(empty["net_pay"], 2),
            "employer_contributions": round(
                empty["employer_contributions"], 2
            ),
            "payroll_entries": payroll_entries,
        }
    )
    if empty["payroll_payable"] and empty["payroll_payable"] > 0:
        empty["status"] = "warning"
    return empty


def get_school_financial_operations(term, settings):
    """Read school-wide financial operations from ERPNext's submitted ledger."""
    if not settings.get("track_school_finance"):
        return {"enabled": False, "status": "disabled"}
    if not _doctype_exists("GL Entry") or not _doctype_exists("Account"):
        return {
            "enabled": True,
            "available": False,
            "status": "no_data",
            "message": "ERPNext accounting doctypes are not available.",
        }

    company = _company(settings)
    if not company or not frappe.db.exists("Company", company):
        return {
            "enabled": True,
            "available": False,
            "status": "setup_required",
            "message": "Select the School Finance Company in School MIS Settings.",
        }

    cost_center = settings.get("finance_cost_center")
    as_of = min(getdate(term.end_date), getdate(nowdate()))
    income_accounts = _leaf_accounts(company, root_type="Income")
    expense_accounts = _leaf_accounts(company, root_type="Expense")
    cash_accounts = _leaf_accounts(
        company,
        account_types=("Bank", "Cash"),
    )

    income_gl = _sum_gl(
        company, income_accounts, term.start_date, as_of, cost_center
    )
    expense_gl = _sum_gl(
        company, expense_accounts, term.start_date, as_of, cost_center
    )
    cash_gl = _sum_gl(company, cash_accounts, end_date=as_of)

    income = max(0, income_gl["credit"] - income_gl["debit"])
    expenses = max(0, expense_gl["debit"] - expense_gl["credit"])
    cash_and_bank = cash_gl["debit"] - cash_gl["credit"]
    operating_surplus = income - expenses

    wage_accounts = _account_and_descendants(
        settings.get("wage_expense_account"), company
    )
    wage_gl = _sum_gl(
        company, wage_accounts, term.start_date, as_of, cost_center
    )
    wages = max(0, wage_gl["debit"] - wage_gl["credit"])

    fee_accounts = _account_and_descendants(
        settings.get("student_fee_income_account"), company
    )
    fee_gl = _sum_gl(
        company, fee_accounts, term.start_date, as_of, cost_center
    )
    fee_income = max(0, fee_gl["credit"] - fee_gl["debit"])

    currency = frappe.get_cached_value("Company", company, "default_currency")
    budget = _budget_summary(company, as_of, cost_center)
    fund_requests = _fund_request_summary(term, company, cost_center)
    payroll = _payroll_summary(
        term, settings, company, cost_center, as_of
    )
    status = "healthy"
    if operating_surplus < 0 or budget.get("status") == "warning":
        status = "warning"

    return {
        "enabled": True,
        "available": True,
        "status": status,
        "company": company,
        "cost_center": cost_center,
        "scope": cost_center or company,
        "currency": currency,
        "as_of": str(as_of),
        "cash_and_bank": round(cash_and_bank, 2),
        "term_income": round(income, 2),
        "term_expenses": round(expenses, 2),
        "operating_surplus": round(operating_surplus, 2),
        "operating_margin": _percentage(operating_surplus, income),
        "student_fee_income": round(fee_income, 2),
        "student_fee_income_account_configured": bool(
            settings.get("student_fee_income_account")
        ),
        "other_income": round(max(0, income - fee_income), 2),
        "wage_expense": round(wages, 2),
        "wage_expense_account_configured": bool(
            settings.get("wage_expense_account")
        ),
        "other_expenses": round(max(0, expenses - wages), 2),
        "budget": budget,
        "fund_requests": fund_requests,
        "payroll": payroll,
    }
