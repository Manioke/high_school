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


def _cost_center_scope(company, cost_center):
    """Return the selected Cost Center and every descendant posting node."""
    if not cost_center:
        return None
    node = frappe.db.get_value(
        "Cost Center",
        cost_center,
        ["company", "lft", "rgt", "is_group"],
        as_dict=True,
    )
    if not node or node.company != company:
        return []
    if not node.is_group:
        return [cost_center]
    descendants = frappe.get_all(
        "Cost Center",
        filters={
            "company": company,
            "lft": [">", node.lft],
            "rgt": ["<", node.rgt],
        },
        pluck="name",
    )
    return [cost_center, *descendants]


def _sum_gl(
    company,
    accounts,
    start_date=None,
    end_date=None,
    cost_centers=None,
    extra_filters=None,
):
    """Sum submitted ledger rows using Frappe v16 aggregate-field syntax."""
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
    if cost_centers:
        filters["cost_center"] = ["in", list(set(cost_centers))]
    filters.update(extra_filters or {})

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


def _gl_breakdown(
    company,
    accounts,
    start_date,
    end_date,
    cost_centers,
    balance_type,
):
    if not accounts:
        return []
    filters = {
        "company": company,
        "account": ["in", list(set(accounts))],
        "posting_date": ["between", [start_date, end_date]],
    }
    if "is_cancelled" in _meta_fields("GL Entry"):
        filters["is_cancelled"] = 0
    if cost_centers:
        filters["cost_center"] = ["in", list(set(cost_centers))]
    rows = frappe.get_all(
        "GL Entry",
        filters=filters,
        fields=[
            "account",
            "cost_center",
            {"SUM": "debit", "as": "debit"},
            {"SUM": "credit", "as": "credit"},
        ],
        group_by="account, cost_center",
        limit_page_length=0,
    )
    result = []
    for row in rows:
        if balance_type == "income":
            amount = flt(row.get("credit")) - flt(row.get("debit"))
        else:
            amount = flt(row.get("debit")) - flt(row.get("credit"))
        if amount:
            account = frappe.get_cached_value(
                "Account",
                row.get("account"),
                ["account_name", "parent_account"],
                as_dict=True,
            ) or {}
            parent_name = (
                frappe.get_cached_value(
                    "Account", account.get("parent_account"), "account_name"
                )
                if account.get("parent_account")
                else None
            )
            result.append(
                {
                    "type": balance_type.title(),
                    "account": row.get("account"),
                    "account_name": account.get("account_name") or row.get("account"),
                    "category": parent_name or account.get("parent_account") or "Other",
                    "cost_center": row.get("cost_center"),
                    "amount": round(amount, 2),
                }
            )
    return sorted(result, key=lambda row: abs(row["amount"]), reverse=True)[:50]


def _reporting_date(term):
    """Use a coherent range for current, past, and future demonstration terms."""
    today = getdate(nowdate())
    start_date = getdate(term.start_date)
    end_date = getdate(term.end_date)
    if today < start_date:
        return end_date, "future_term_preview"
    if today > end_date:
        return end_date, "closed_term"
    return today, "current_term"


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


def _budget_matches_date(budget, budget_fields, as_of):
    if "fiscal_year" in budget_fields:
        year = frappe.db.get_value(
            "Fiscal Year",
            budget.get("fiscal_year"),
            ["year_start_date", "year_end_date"],
            as_dict=True,
        )
        return bool(
            year
            and getdate(year.year_start_date) <= getdate(as_of)
            and getdate(year.year_end_date) >= getdate(as_of)
        )

    from_year = budget.get("from_fiscal_year")
    to_year = budget.get("to_fiscal_year")
    if not from_year and not to_year:
        return True
    from_start = frappe.db.get_value(
        "Fiscal Year", from_year or to_year, "year_start_date"
    )
    to_end = frappe.db.get_value(
        "Fiscal Year", to_year or from_year, "year_end_date"
    )
    return bool(
        from_start
        and to_end
        and getdate(from_start) <= getdate(as_of) <= getdate(to_end)
    )


def _budget_components(budget):
    rows = budget.get("accounts") or []
    if rows:
        return [
            {
                "account": row.get("account"),
                "budget_amount": flt(row.get("budget_amount")),
            }
            for row in rows
            if row.get("account")
        ]
    if budget.get("account"):
        return [
            {
                "account": budget.get("account"),
                "budget_amount": flt(budget.get("budget_amount")),
            }
        ]
    return []


def _budget_summary(company, as_of, selected_cost_centers):
    empty = {
        "available": _doctype_exists("Budget"),
        "status": "no_data",
        "fiscal_year": None,
        "budget_count": 0,
        "budget_total": 0.0,
        "used": 0.0,
        "remaining": 0.0,
        "utilisation_rate": None,
        "rows": [],
    }
    if not empty["available"] or not _doctype_exists("Fiscal Year"):
        return empty
    fiscal_year = _fiscal_year(as_of)
    if not fiscal_year:
        return empty
    empty["fiscal_year"] = fiscal_year.name

    budget_fields = _meta_fields("Budget")
    budget_names = frappe.get_all(
        "Budget",
        filters={"company": company, "docstatus": 1},
        pluck="name",
    )
    gl_fields = _meta_fields("GL Entry")
    rows = []

    for name in budget_names:
        budget = frappe.get_doc("Budget", name)
        if not _budget_matches_date(budget, budget_fields, as_of):
            continue

        budget_against = budget.get("budget_against") or "Cost Center"
        dimension_field = frappe.scrub(budget_against)
        dimension_value = budget.get(dimension_field)
        if (
            selected_cost_centers
            and budget_against == "Cost Center"
            and dimension_value not in selected_cost_centers
        ):
            continue

        budget_cost_centers = selected_cost_centers
        extra_filters = {}
        if budget_against == "Cost Center" and dimension_value:
            budget_cost_centers = _cost_center_scope(company, dimension_value)
        elif dimension_value and dimension_field in gl_fields:
            extra_filters[dimension_field] = dimension_value

        for component in _budget_components(budget):
            account = component["account"]
            accounts = _account_and_descendants(account, company)
            totals = _sum_gl(
                company,
                accounts,
                fiscal_year.year_start_date,
                min(getdate(as_of), getdate(fiscal_year.year_end_date)),
                budget_cost_centers,
                extra_filters,
            )
            actual = max(0, totals["debit"] - totals["credit"])
            amount = max(0, component["budget_amount"])
            rows.append(
                {
                    "budget": name,
                    "budget_against": budget_against,
                    "dimension": dimension_value,
                    "account": account,
                    "budget_amount": round(amount, 2),
                    "actual_expense": round(actual, 2),
                    "remaining": round(amount - actual, 2),
                    "utilisation_rate": _percentage(actual, amount),
                }
            )

    if not rows:
        return empty
    budget_total = sum(row["budget_amount"] for row in rows)
    used = sum(row["actual_expense"] for row in rows)
    utilisation = _percentage(used, budget_total)
    return {
        "available": True,
        "status": "warning" if utilisation is not None and utilisation > 100 else "healthy",
        "fiscal_year": fiscal_year.name,
        "budget_count": len({row["budget"] for row in rows}),
        "budget_total": round(budget_total, 2),
        "used": round(used, 2),
        "remaining": round(budget_total - used, 2),
        "utilisation_rate": utilisation,
        "rows": rows,
    }


def _fund_request_summary(term, company, selected_cost_centers):
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
    if selected_cost_centers:
        filters["cost_center"] = ["in", selected_cost_centers]
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
        limit_page_length=0,
    )
    for row in rows:
        empty["requested"] += flt(row.get("requested_amount"))
        empty["approved"] += flt(row.get("approved_amount"))
        empty["disbursed"] += flt(row.get("disbursed_amount"))
        empty["outstanding"] += flt(row.get("outstanding_amount"))
        if row.get("status") in OPEN_FUND_REQUEST_STATUSES:
            empty["open_count"] += 1
    empty["request_count"] = len(rows)
    empty["items"] = rows[:50]
    for key in ("requested", "approved", "disbursed", "outstanding"):
        empty[key] = round(empty[key], 2)
    return empty


def _payroll_summary(term, settings, company, selected_cost_centers, as_of):
    enabled = bool(settings.get("track_hr_payroll"))
    available = _doctype_exists("Salary Slip") and _doctype_exists("Payroll Entry")
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
        "payroll_payable_available": False,
        "payroll_entries": [],
        "scope_warning": None,
    }
    if not enabled or not available:
        return empty

    slip_fields = _meta_fields("Salary Slip")
    slip_filters = {"company": company, "docstatus": 1}
    if "start_date" in slip_fields and "end_date" in slip_fields:
        slip_filters["start_date"] = ["<=", as_of]
        slip_filters["end_date"] = [">=", term.start_date]
    if selected_cost_centers and "cost_center" in slip_fields:
        slip_filters["cost_center"] = ["in", selected_cost_centers]
    elif selected_cost_centers and "payroll_entry" not in slip_fields:
        empty["scope_warning"] = (
            "Salary Slips expose neither Cost Center nor Payroll Entry; operational payroll "
            "totals are company-wide. Ledger wage expense remains Cost Center scoped."
        )
    wanted_slip_fields = [
        "name",
        "employee",
        "gross_pay",
        "net_pay",
        "total_deduction",
        "total_employer_contribution",
        "payroll_entry",
    ]
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=slip_filters,
        fields=[
            field for field in wanted_slip_fields
            if field == "name" or field in slip_fields
        ],
        limit_page_length=0,
    )
    entry_fields = _meta_fields("Payroll Entry")
    entry_filters = {"company": company, "docstatus": ["<", 2]}
    if "start_date" in entry_fields and "end_date" in entry_fields:
        entry_filters["start_date"] = ["<=", as_of]
        entry_filters["end_date"] = [">=", term.start_date]
    if selected_cost_centers and "cost_center" in entry_fields:
        entry_filters["cost_center"] = ["in", selected_cost_centers]
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
            field for field in wanted_entry_fields
            if field == "name" or field in entry_fields
        ],
        order_by=(
            "start_date desc, modified desc"
            if "start_date" in entry_fields
            else "modified desc"
        ),
        limit_page_length=0,
    )

    if selected_cost_centers and "cost_center" not in slip_fields:
        if "payroll_entry" in slip_fields:
            matching_entries = {row.get("name") for row in payroll_entries}
            salary_slips = [
                slip
                for slip in salary_slips
                if slip.get("payroll_entry") in matching_entries
            ]
            empty["scope_warning"] = (
                "Salary Slips have no Cost Center field, so operational payroll totals are "
                "scoped through their matching Payroll Entries. Wage expense and salary "
                "budget actual remain sourced from General Ledger Cost Centers."
            )

    employees = set()
    for slip in salary_slips:
        if slip.get("employee"):
            employees.add(slip.get("employee"))
        empty["gross_pay"] += flt(slip.get("gross_pay"))
        empty["deductions"] += flt(slip.get("total_deduction"))
        empty["net_pay"] += flt(slip.get("net_pay"))
        empty["employer_contributions"] += flt(
            slip.get("total_employer_contribution")
        )

    payable_accounts = _account_and_descendants(
        settings.get("payroll_payable_account"), company
    )
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
            "employer_contributions": round(empty["employer_contributions"], 2),
            "payroll_entries": payroll_entries[:50],
        }
    )
    if empty["payroll_payable"] and empty["payroll_payable"] > 0:
        empty["status"] = "warning"
    return empty


def get_school_financial_operations(term, settings):
    """Read whole-school finance from ERPNext and Frappe HR records."""
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

    selected_cost_center = settings.get("finance_cost_center")
    selected_cost_centers = _cost_center_scope(company, selected_cost_center)
    if selected_cost_center and not selected_cost_centers:
        return {
            "enabled": True,
            "available": False,
            "status": "setup_required",
            "message": (
                "The School Finance Cost Center does not belong to the configured Company."
            ),
        }

    as_of, reporting_basis = _reporting_date(term)
    income_accounts = _leaf_accounts(company, root_type="Income")
    expense_accounts = _leaf_accounts(company, root_type="Expense")
    cash_accounts = _leaf_accounts(company, account_types=("Bank", "Cash"))

    income_gl = _sum_gl(
        company,
        income_accounts,
        term.start_date,
        as_of,
        selected_cost_centers,
    )
    expense_gl = _sum_gl(
        company,
        expense_accounts,
        term.start_date,
        as_of,
        selected_cost_centers,
    )
    cash_gl = _sum_gl(company, cash_accounts, end_date=as_of)

    income = max(0, income_gl["credit"] - income_gl["debit"])
    expenses = max(0, expense_gl["debit"] - expense_gl["credit"])
    cash_and_bank = cash_gl["debit"] - cash_gl["credit"]
    operating_surplus = income - expenses

    fiscal_year = _fiscal_year(as_of)
    fiscal_profit_and_loss = {
        "available": False,
        "fiscal_year": None,
        "start_date": None,
        "end_date": str(as_of),
        "income": 0.0,
        "expenses": 0.0,
        "net_result": 0.0,
        "income_breakdown": [],
        "expense_breakdown": [],
    }
    if fiscal_year:
        fiscal_income_gl = _sum_gl(
            company,
            income_accounts,
            fiscal_year.year_start_date,
            as_of,
            selected_cost_centers,
        )
        fiscal_expense_gl = _sum_gl(
            company,
            expense_accounts,
            fiscal_year.year_start_date,
            as_of,
            selected_cost_centers,
        )
        fiscal_income = max(
            0, fiscal_income_gl["credit"] - fiscal_income_gl["debit"]
        )
        fiscal_expenses = max(
            0, fiscal_expense_gl["debit"] - fiscal_expense_gl["credit"]
        )
        fiscal_profit_and_loss.update(
            {
                "available": True,
                "fiscal_year": fiscal_year.name,
                "start_date": str(fiscal_year.year_start_date),
                "income": round(fiscal_income, 2),
                "expenses": round(fiscal_expenses, 2),
                "net_result": round(fiscal_income - fiscal_expenses, 2),
                "income_breakdown": _gl_breakdown(
                    company,
                    income_accounts,
                    fiscal_year.year_start_date,
                    as_of,
                    selected_cost_centers,
                    "income",
                ),
                "expense_breakdown": _gl_breakdown(
                    company,
                    expense_accounts,
                    fiscal_year.year_start_date,
                    as_of,
                    selected_cost_centers,
                    "expense",
                ),
            }
        )

    wage_accounts = _account_and_descendants(
        settings.get("wage_expense_account"), company
    )
    wage_gl = _sum_gl(
        company,
        wage_accounts,
        term.start_date,
        as_of,
        selected_cost_centers,
    )
    wages = max(0, wage_gl["debit"] - wage_gl["credit"])

    fee_accounts = _account_and_descendants(
        settings.get("student_fee_income_account"), company
    )
    fee_gl = _sum_gl(
        company,
        fee_accounts,
        term.start_date,
        as_of,
        selected_cost_centers,
    )
    fee_income = max(0, fee_gl["credit"] - fee_gl["debit"])

    currency = frappe.get_cached_value("Company", company, "default_currency")
    budget = _budget_summary(company, as_of, selected_cost_centers)
    fund_requests = _fund_request_summary(term, company, selected_cost_centers)
    payroll = _payroll_summary(
        term, settings, company, selected_cost_centers, as_of
    )
    payroll["wage_gl_expense"] = round(wages, 2)
    payroll_difference = round(flt(payroll.get("gross_pay")) - wages, 2)
    payroll["gross_to_wage_gl_difference"] = payroll_difference
    payroll["reconciliation_status"] = (
        "matched" if abs(payroll_difference) <= 0.01 else "warning"
    )
    payroll["reconciliation_message"] = (
        "Submitted gross payroll matches the posted wage expense."
        if payroll["reconciliation_status"] == "matched"
        else (
            "Submitted gross payroll differs from the wage expense posted to the "
            "selected term and Cost Center scope by {0:,.2f}. Review each Payroll "
            "Entry's salary-accrual Journal Entry, posting date, expense account, "
            "and Cost Center."
        ).format(abs(payroll_difference))
    )
    income_breakdown = _gl_breakdown(
        company,
        income_accounts,
        term.start_date,
        as_of,
        selected_cost_centers,
        "income",
    )
    expense_breakdown = _gl_breakdown(
        company,
        expense_accounts,
        term.start_date,
        as_of,
        selected_cost_centers,
        "expense",
    )

    diagnostics = []
    if selected_cost_center and len(selected_cost_centers) > 1:
        diagnostics.append(
            "{0} is a group scope; {1} descendant Cost Centers are included.".format(
                selected_cost_center, len(selected_cost_centers) - 1
            )
        )
    if reporting_basis == "future_term_preview":
        diagnostics.append(
            "The selected School Term has not started. This preview includes submitted "
            "future-dated accounting entries through {0}; it is intended for testing and "
            "planning, not a statement that the transactions have already occurred.".format(
                as_of
            )
        )
    if payroll.get("salary_slip_count") and not wages:
        diagnostics.append(
            "Payroll records exist but no wage expense matched the term ledger scope. "
            "Submit Salary Slips from Payroll Entry, check the Salary Component expense "
            "accounts, posting date, and payroll Cost Center."
        )
    elif payroll.get("salary_slip_count") and payroll.get("reconciliation_status") == "warning":
        diagnostics.append(payroll["reconciliation_message"])
    if not expenses:
        diagnostics.append(
            "No submitted expense GL entries matched the selected term and Cost Center scope."
        )

    status = "healthy"
    if (
        operating_surplus < 0
        or budget.get("status") == "warning"
        or payroll.get("reconciliation_status") == "warning"
    ):
        status = "warning"

    return {
        "enabled": True,
        "available": True,
        "status": status,
        "company": company,
        "cost_center": selected_cost_center,
        "cost_center_count": len(selected_cost_centers or []),
        "scope": selected_cost_center or company,
        "currency": currency,
        "as_of": str(as_of),
        "reporting_basis": reporting_basis,
        "cash_scope": company,
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
        "fiscal_profit_and_loss": fiscal_profit_and_loss,
        "fund_requests": fund_requests,
        "payroll": payroll,
        "income_breakdown": income_breakdown,
        "expense_breakdown": expense_breakdown,
        "diagnostics": diagnostics,
    }
