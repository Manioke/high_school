from unittest import TestCase

from high_school.high_school.performance_period_setup import _period_name, _selected_groups


class TestSchoolPerformancePeriodSetup(TestCase):
	def test_period_name_uses_term_and_main_group(self):
		self.assertEqual(_period_name("2026-Term1", "F5-A-2026"), "2026-Term1 - F5-A-2026")

	def test_only_checked_groups_are_selected(self):
		rows = [
			{"create_period": 1, "student_group": "F5-A-2026"},
			{"create_period": 0, "student_group": "F5-COM-01-2026"},
		]
		self.assertEqual(_selected_groups(rows), ["F5-A-2026"])
