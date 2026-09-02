import frappe

from high_school.high_school.mis.attendance import (
    COURSE_ATTENDANCE,
    DAILY_ATTENDANCE,
    analyse_attendance,
)
from high_school.high_school.mis.academic import get_performance_summary
from high_school.high_school.mis.finance import get_financial_mis


def _indicator(label, current, previous, unit="%", higher_is_better=True):
    if current is None or previous is None:
        direction = "no_data"
        change = None
    else:
        change = round(float(current) - float(previous), 1)
        adjusted = change if higher_is_better else -change
        if adjusted >= 1:
            direction = "improving"
        elif adjusted <= -1:
            direction = "declining"
        else:
            direction = "stable"

    return {
        "label": label,
        "current": current,
        "previous": previous,
        "change": change,
        "unit": unit,
        "direction": direction,
    }


def _attendance_rate(term, attendance_type, settings):
    result = analyse_attendance(
        start_date=term.start_date,
        end_date=term.end_date,
        attendance_type=attendance_type,
        settings=settings,
    )
    return (result.get("summary") or {}).get("attendance_rate")


def _previous_term(term):
    fields = [
        "name",
        "academic_year",
        "term",
        "start_date",
        "end_date",
    ]
    rows = frappe.get_all(
        "School Term",
        filters={
            "academic_year": term.academic_year,
            "end_date": ["<", term.start_date],
        },
        fields=fields,
        order_by="end_date desc",
        limit_page_length=1,
    )
    if not rows:
        rows = frappe.get_all(
            "School Term",
            filters={"end_date": ["<", term.start_date]},
            fields=fields,
            order_by="end_date desc",
            limit_page_length=1,
        )
    return rows[0] if rows else None


def get_school_direction(term, current_data, settings):
    """Compare stable outcomes with the preceding School Term."""
    previous = _previous_term(term)
    indicators = []

    if previous:
        attendance = current_data.get("attendance", {})

        if attendance.get("daily", {}).get("enabled"):
            current = (
                attendance.get("daily", {})
                .get("summary", {})
                .get("attendance_rate")
            )
            indicators.append(
                _indicator(
                    "Daily Attendance",
                    current,
                    _attendance_rate(previous, DAILY_ATTENDANCE, settings),
                )
            )

        if attendance.get("course", {}).get("enabled"):
            current = (
                attendance.get("course", {})
                .get("performance", {})
                .get("summary", {})
                .get("attendance_rate")
            )
            indicators.append(
                _indicator(
                    "Course Attendance",
                    current,
                    _attendance_rate(previous, COURSE_ATTENDANCE, settings),
                )
            )

        current_average = (
            current_data.get("academics", {})
            .get("performance", {})
            .get("school_average")
        )
        previous_average = get_performance_summary(
            previous.name
        ).get("school_average")
        indicators.append(
            _indicator(
                "Academic Performance",
                current_average,
                previous_average,
            )
        )

        finance = current_data.get("finance", {})
        if finance.get("enabled") and finance.get("available"):
            previous_finance = get_financial_mis(previous, settings)
            indicators.append(
                _indicator(
                    "Fee Collection",
                    finance.get("collection_rate"),
                    previous_finance.get("collection_rate"),
                )
            )

    finance = current_data.get("finance", {})
    finance_progress = None
    finance_target = finance.get("target")
    if finance.get("enabled") and finance.get("available"):
        collection_rate = finance.get("collection_rate")
        if collection_rate is not None and finance_target is not None:
            finance_progress = round(
                float(collection_rate) - float(finance_target),
                1,
            )

    directions = {
        row["direction"]
        for row in indicators
        if row["direction"] != "no_data"
    }
    if not directions:
        status = "no_data"
        label = "Not Enough History"
    elif directions == {"stable"}:
        status = "stable"
        label = "Holding Steady"
    elif "improving" in directions and directions <= {"improving", "stable"}:
        status = "improving"
        label = "Improving"
    elif "declining" in directions and directions <= {"declining", "stable"}:
        status = "declining"
        label = "Needs Attention"
    else:
        status = "mixed"
        label = "Mixed Direction"

    return {
        "status": status,
        "label": label,
        "previous_term": (
            {
                "name": previous.name,
                "academic_year": previous.academic_year,
                "term": previous.term,
                "start_date": str(previous.start_date),
                "end_date": str(previous.end_date),
            }
            if previous
            else None
        ),
        "indicators": indicators,
        "finance_progress_to_target": finance_progress,
        "finance_collection_rate": finance.get("collection_rate"),
        "finance_target": finance_target,
    }
