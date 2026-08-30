from unittest import TestCase

from high_school.high_school.assessment_plan_setup import _deduplicate_candidates


class TestSchoolAssessmentPlanSetup(TestCase):
	def test_candidates_are_unique_by_group_and_course(self):
		rows = [
			{"student_group": "F5-A", "course": "English", "instructor": None},
			{"student_group": "F5-A", "course": "English", "instructor": "Teacher 1"},
			{"student_group": "F5-A", "course": "Mathematics", "instructor": "Teacher 2"},
		]
		result = _deduplicate_candidates(rows)
		self.assertEqual(len(result), 2)
		self.assertEqual(result[0]["instructor"], "Teacher 1")
		self.assertEqual(result[0]["instructor_mapping_status"], "Resolved")

	def test_conflicting_scheduled_instructors_are_not_silently_selected(self):
		rows = [
			{"student_group": "F5-A", "course": "English", "instructor": "Teacher 1"},
			{"student_group": "F5-A", "course": "English", "instructor": "Teacher 2"},
		]
		result = _deduplicate_candidates(rows)
		self.assertEqual(result[0]["instructor_mapping_status"], "Conflicting")
		self.assertIsNone(result[0]["instructor"])
