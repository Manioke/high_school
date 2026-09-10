from unittest import TestCase

import frappe

from high_school.high_school.student_interventions import (
    _leading_absence_count,
    evaluate_academic_trigger,
)


class TestAcademicInterventionTrigger(TestCase):
    def test_absolute_school_threshold_triggers(self):
        result = evaluate_academic_trigger(49, [49, 55, 60], 50, 1.5)
        self.assertTrue(result["triggered"])
        self.assertTrue(result["absolute_trigger"])

    def test_statistical_trigger_requires_five_peer_scores(self):
        result = evaluate_academic_trigger(60, [60, 80, 82, 84], 50, 1.5)
        self.assertFalse(result["statistical_trigger"])

        result = evaluate_academic_trigger(60, [60, 80, 82, 84, 86], 50, 1.5)
        self.assertTrue(result["statistical_trigger"])

    def test_healthy_score_does_not_trigger(self):
        result = evaluate_academic_trigger(75, [70, 72, 75, 78, 80], 50, 1.5)
        self.assertFalse(result["triggered"])


class TestCourseAttendanceInterventionTrigger(TestCase):
    def test_only_leading_consecutive_absences_count(self):
        rows = [
            frappe._dict(status="Absent"),
            frappe._dict(status="Absent"),
            frappe._dict(status="Present"),
            frappe._dict(status="Absent"),
        ]
        self.assertEqual(_leading_absence_count(rows), 2)

    def test_present_latest_record_resets_consecutive_absences(self):
        rows = [
            frappe._dict(status="Present"),
            frappe._dict(status="Absent"),
            frappe._dict(status="Absent"),
        ]
        self.assertEqual(_leading_absence_count(rows), 0)
