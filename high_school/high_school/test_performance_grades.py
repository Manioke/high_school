from unittest import TestCase
from unittest.mock import patch

import frappe

from high_school.high_school.performance import _course_grade


class TestPerformanceGrades(TestCase):
	@patch("high_school.high_school.performance.frappe.get_all")
	def test_course_grade_uses_plan_grading_scale_thresholds(self, get_all):
		get_all.return_value = [
			frappe._dict(grade_code="A", threshold=80),
			frappe._dict(grade_code="B", threshold=70),
			frappe._dict(grade_code="C", threshold=50),
		]
		plans = [frappe._dict(grading_scale="Standard Grading")]

		self.assertEqual(_course_grade(plans, 74.5), "B")
		get_all.assert_called_once_with(
			"Grading Scale Interval",
			filters={"parent": "Standard Grading"},
			fields=["grade_code", "threshold"],
			order_by="threshold desc",
			limit_page_length=0,
		)

	def test_course_grade_is_blank_without_a_scale(self):
		self.assertEqual(_course_grade([frappe._dict(grading_scale=None)], 74.5), "")
