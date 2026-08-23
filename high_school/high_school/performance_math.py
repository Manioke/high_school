from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


MISSING_INCOMPLETE = "Incomplete and Do Not Rank"
MISSING_ZERO = "Count Missing as Zero"
MISSING_IGNORE = "Ignore Missing Components"

RANK_COMPETITION = "Competition (1, 2, 2, 4)"
RANK_DENSE = "Dense (1, 2, 2, 3)"


def as_decimal(value) -> Decimal:
	if value in (None, ""):
		return Decimal("0")
	return Decimal(str(value))


def calculate_weighted_percentage(component_scores, missing_policy=MISSING_INCOMPLETE):
	"""Return (percentage, is_complete) for one course.

	component_scores is an iterable containing ``percentage``, ``weight`` and
	``present``. Percentages and weights are expressed on a 0-100 scale.
	"""
	rows = list(component_scores)
	missing = [row for row in rows if not row.get("present")]

	if missing and missing_policy == MISSING_INCOMPLETE:
		return None, False

	present_rows = [row for row in rows if row.get("present")]
	if missing_policy == MISSING_IGNORE:
		weight_total = sum(as_decimal(row.get("weight")) for row in present_rows)
		if not weight_total:
			return None, False
		weighted = sum(
			as_decimal(row.get("percentage")) * as_decimal(row.get("weight"))
			for row in present_rows
		)
		return weighted / weight_total, True

	weighted = sum(
		as_decimal(row.get("percentage")) * as_decimal(row.get("weight"))
		for row in present_rows
	)
	return weighted / Decimal("100"), True


def calculate_overall_percentage(course_percentages):
	values = [as_decimal(value) for value in course_percentages if value is not None]
	if not values:
		return None
	return sum(values) / Decimal(len(values))


def assign_ranks(rows, method=RANK_COMPETITION):
	"""Rank complete rows in place using their unrounded overall percentage."""
	rankable = [row for row in rows if row.get("overall_percentage") is not None and row.get("is_complete")]
	rankable.sort(
		key=lambda row: (
			-as_decimal(row.get("overall_percentage")),
			str(row.get("student") or ""),
		)
	)

	previous_score = None
	previous_rank = 0
	dense_rank = 0
	for index, row in enumerate(rankable, start=1):
		score = as_decimal(row.get("overall_percentage"))
		if score != previous_score:
			dense_rank += 1
			previous_rank = dense_rank if method == RANK_DENSE else index
			previous_score = score
		row["rank"] = previous_rank
		row["rank_out_of"] = len(rankable)

	return rows


def rounded(value, precision=2):
	if value is None:
		return None
	quantizer = Decimal("1").scaleb(-int(precision))
	return as_decimal(value).quantize(quantizer, rounding=ROUND_HALF_UP)
