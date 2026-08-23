from decimal import Decimal
from unittest import TestCase

from high_school.high_school.performance_math import (
	MISSING_IGNORE,
	MISSING_INCOMPLETE,
	MISSING_ZERO,
	RANK_COMPETITION,
	RANK_DENSE,
	assign_ranks,
	calculate_overall_percentage,
	calculate_weighted_percentage,
)


class TestPerformanceMath(TestCase):
	def test_independent_result(self):
		percentage, complete = calculate_weighted_percentage(
			[{"percentage": 82, "weight": 100, "present": True}]
		)
		self.assertEqual(percentage, Decimal("82"))
		self.assertTrue(complete)

	def test_combined_result(self):
		percentage, complete = calculate_weighted_percentage(
			[
				{"percentage": 70, "weight": 40, "present": True},
				{"percentage": 80, "weight": 60, "present": True},
			]
		)
		self.assertEqual(percentage, Decimal("76"))
		self.assertTrue(complete)

	def test_missing_policies(self):
		rows = [
			{"percentage": 70, "weight": 40, "present": True},
			{"percentage": None, "weight": 60, "present": False},
		]
		self.assertEqual(calculate_weighted_percentage(rows, MISSING_INCOMPLETE), (None, False))
		self.assertEqual(calculate_weighted_percentage(rows, MISSING_ZERO), (Decimal("28"), True))
		self.assertEqual(calculate_weighted_percentage(rows, MISSING_IGNORE), (Decimal("70"), True))

	def test_overall_is_equal_subject_average(self):
		self.assertEqual(calculate_overall_percentage([76, 71, 87]), Decimal("78"))

	def test_competition_and_dense_ranking(self):
		base = [
			{"student": "A", "overall_percentage": 90, "is_complete": True},
			{"student": "B", "overall_percentage": 80, "is_complete": True},
			{"student": "C", "overall_percentage": 80, "is_complete": True},
			{"student": "D", "overall_percentage": 70, "is_complete": True},
			{"student": "E", "overall_percentage": 99, "is_complete": False},
		]
		competition = assign_ranks([dict(row) for row in base], RANK_COMPETITION)
		self.assertEqual([row.get("rank") for row in competition], [1, 2, 2, 4, None])
		dense = assign_ranks([dict(row) for row in base], RANK_DENSE)
		self.assertEqual([row.get("rank") for row in dense], [1, 2, 2, 3, None])
