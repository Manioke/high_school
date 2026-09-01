from collections import defaultdict

import frappe

from frappe.utils import (
    date_diff,
    flt,
    getdate,
    nowdate,
)


def _percentage(numerator, denominator):
    if not denominator:
        return None
    return round((flt(numerator) / flt(denominator)) * 100, 1)


def _meta_fields(doctype):
    if not frappe.db.exists("DocType", doctype):
        return set()
    return {
        field.fieldname
        for field in frappe.get_meta(doctype).fields
    }


def _school_fee_filters(invoice_fields, academic_year):
    filters = {"docstatus": 1}

    if "academic_year" in invoice_fields:
        filters["academic_year"] = academic_year
        return filters, "Academic Year"

    if "fee_schedule" in invoice_fields:
        schedule_fields = _meta_fields("Fee Schedule")
        if "academic_year" in schedule_fields:
            schedules = frappe.get_all(
                "Fee Schedule",
                filters={"academic_year": academic_year},
                pluck="name",
            )
            if not schedules:
                return None, "Fee Schedule"
            filters["fee_schedule"] = ["in", schedules]
        else:
            filters["fee_schedule"] = ["is", "set"]
        return filters, "Fee Schedule"

    if "student" in invoice_fields:
        filters["student"] = ["is", "set"]
        return filters, "Student"

    return None, None


def _student_batches(students, academic_year):
    if not students or not frappe.db.exists("DocType", "Program Enrollment"):
        return {}

    fields = _meta_fields("Program Enrollment")
    if "student" not in fields:
        return {}

    query_fields = ["student"]
    batch_field = next(
        (
            name
            for name in ("student_batch_name", "student_batch", "batch")
            if name in fields
        ),
        None,
    )
    if not batch_field:
        return {}
    query_fields.append(batch_field)

    filters = {
        "student": ["in", list(students)],
        "docstatus": ["<", 2],
    }
    if "academic_year" in fields:
        filters["academic_year"] = academic_year

    rows = frappe.get_all(
        "Program Enrollment",
        filters=filters,
        fields=query_fields,
        order_by="creation desc",
    )

    result = {}
    for row in rows:
        result.setdefault(row.student, row.get(batch_field))
    return result


def get_financial_mis(term, settings):
    """Summarize the existing student Sales Invoices for an academic year."""
    target = flt(settings.get("fee_collection_target") or 90)
    overdue_target = flt(settings.get("overdue_fee_target") or 5)

    if not settings.get("track_student_finance"):
        return {
            "enabled": False,
            "status": "disabled",
            "target": target,
        }

    invoice_fields = _meta_fields("Sales Invoice")
    if not invoice_fields:
        return {
            "enabled": True,
            "available": False,
            "status": "no_data",
            "message": "Sales Invoice is not available.",
            "target": target,
        }

    filters, scope_source = _school_fee_filters(
        invoice_fields,
        term.academic_year,
    )
    if filters is None:
        return {
            "enabled": True,
            "available": False,
            "status": "no_data",
            "message": (
                "Sales Invoice has no Student, Fee Schedule, or Academic Year "
                "field that can identify school fees safely."
            ),
            "target": target,
        }

    wanted_fields = [
        "name",
        "posting_date",
        "due_date",
        "status",
        "company",
        "currency",
        "customer",
        "customer_name",
        "student",
        "student_name",
        "fee_schedule",
        "grand_total",
        "outstanding_amount",
        "base_grand_total",
        "base_outstanding_amount",
    ]
    fields = [
        fieldname
        for fieldname in wanted_fields
        if fieldname in invoice_fields or fieldname == "name"
    ]

    invoices = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=fields,
        order_by="due_date asc, posting_date asc",
    )

    if not invoices:
        return {
            "enabled": True,
            "available": True,
            "status": "no_data",
            "target": target,
            "overdue_target": overdue_target,
            "scope_source": scope_source,
            "academic_year": term.academic_year,
            "invoice_count": 0,
            "student_count": 0,
            "invoiced": 0,
            "collected": 0,
            "outstanding": 0,
            "overdue": 0,
            "collection_rate": None,
            "overdue_rate": None,
            "overdue_invoice_count": 0,
            "overdue_student_count": 0,
            "currency": None,
            "ageing": [],
            "batches": [],
            "attention_items": [],
        }

    today = getdate(nowdate())
    use_base = all("base_grand_total" in row for row in invoices)
    total_field = "base_grand_total" if use_base else "grand_total"
    outstanding_field = (
        "base_outstanding_amount"
        if use_base
        else "outstanding_amount"
    )

    invoiced = 0.0
    outstanding = 0.0
    overdue = 0.0
    overdue_invoices = []
    students = set()
    overdue_students = set()
    ageing = {
        "Not Yet Due": 0.0,
        "1–30 Days": 0.0,
        "31–60 Days": 0.0,
        "61+ Days": 0.0,
    }

    for invoice in invoices:
        total = flt(invoice.get(total_field))
        balance = max(0, flt(invoice.get(outstanding_field)))
        invoiced += total
        outstanding += balance

        student = invoice.get("student") or invoice.get("customer")
        if student:
            students.add(student)

        due_date = getdate(invoice.due_date) if invoice.get("due_date") else None
        days_overdue = date_diff(today, due_date) if due_date else 0
        is_overdue = balance > 0 and due_date and days_overdue > 0

        if not is_overdue:
            if balance > 0:
                ageing["Not Yet Due"] += balance
            continue

        overdue += balance
        if student:
            overdue_students.add(student)

        if days_overdue <= 30:
            ageing["1–30 Days"] += balance
        elif days_overdue <= 60:
            ageing["31–60 Days"] += balance
        else:
            ageing["61+ Days"] += balance

        overdue_invoices.append(
            {
                **invoice,
                "student": invoice.get("student") or invoice.get("customer"),
                "student_name": (
                    invoice.get("student_name")
                    or invoice.get("customer_name")
                    or invoice.get("student")
                    or invoice.get("customer")
                ),
                "outstanding": round(balance, 2),
                "days_overdue": days_overdue,
            }
        )

    collected = max(0, invoiced - outstanding)
    collection_rate = _percentage(collected, invoiced)
    overdue_rate = _percentage(overdue, invoiced)

    student_ids = {
        row.get("student")
        for row in invoices
        if row.get("student")
    }
    batch_by_student = _student_batches(
        student_ids,
        term.academic_year,
    )
    batch_totals = defaultdict(
        lambda: {
            "invoiced": 0.0,
            "outstanding": 0.0,
            "students": set(),
        }
    )
    for invoice in invoices:
        student = invoice.get("student")
        batch = batch_by_student.get(student) or "Unassigned"
        values = batch_totals[batch]
        values["invoiced"] += flt(invoice.get(total_field))
        values["outstanding"] += max(0, flt(invoice.get(outstanding_field)))
        if student:
            values["students"].add(student)

    batches = []
    for batch, values in sorted(batch_totals.items()):
        batch_collected = max(0, values["invoiced"] - values["outstanding"])
        batches.append(
            {
                "student_batch": batch,
                "student_count": len(values["students"]),
                "invoiced": round(values["invoiced"], 2),
                "collected": round(batch_collected, 2),
                "outstanding": round(values["outstanding"], 2),
                "collection_rate": _percentage(
                    batch_collected,
                    values["invoiced"],
                ),
            }
        )

    companies = {
        row.get("company")
        for row in invoices
        if row.get("company")
    }
    currencies = {
        row.get("currency")
        for row in invoices
        if row.get("currency")
    }
    currency = None
    if use_base and len(companies) == 1:
        currency = frappe.get_cached_value(
            "Company",
            next(iter(companies)),
            "default_currency",
        )
    elif len(currencies) == 1:
        currency = next(iter(currencies))

    status = "healthy"
    if collection_rate is None:
        status = "no_data"
    elif collection_rate < target or (overdue_rate or 0) > overdue_target:
        status = "warning"

    overdue_invoices.sort(
        key=lambda row: (
            -row["days_overdue"],
            -row["outstanding"],
        )
    )

    return {
        "enabled": True,
        "available": True,
        "status": status,
        "target": target,
        "overdue_target": overdue_target,
        "scope_source": scope_source,
        "academic_year": term.academic_year,
        "invoice_count": len(invoices),
        "student_count": len(students),
        "invoiced": round(invoiced, 2),
        "collected": round(collected, 2),
        "outstanding": round(outstanding, 2),
        "overdue": round(overdue, 2),
        "collection_rate": collection_rate,
        "overdue_rate": overdue_rate,
        "overdue_invoice_count": len(overdue_invoices),
        "overdue_student_count": len(overdue_students),
        "currency": currency,
        "ageing": [
            {
                "bucket": bucket,
                "amount": round(amount, 2),
            }
            for bucket, amount in ageing.items()
        ],
        "batches": batches,
        "attention_items": overdue_invoices[:50],
    }
