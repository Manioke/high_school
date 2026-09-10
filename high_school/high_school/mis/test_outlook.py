from unittest import TestCase

from high_school.high_school.mis.outlook import (
    _normalise_free_text_reason,
    _student_is_inactive,
)


class TestLeavingReasonNormalisation(TestCase):
    def test_maps_common_existing_reason_text(self):
        self.assertEqual(
            _normalise_free_text_reason("Transferred to another school"),
            "Transferred to Another School",
        )
        self.assertEqual(
            _normalise_free_text_reason("Family moved overseas"),
            "Relocation",
        )
        self.assertEqual(
            _normalise_free_text_reason("Could not afford the fees"),
            "Financial Reasons",
        )

    def test_keeps_unknown_text_in_other_category(self):
        self.assertEqual(_normalise_free_text_reason("Personal circumstances"), "Other")
        self.assertIsNone(_normalise_free_text_reason(""))


class TestStudentEnrolmentState(TestCase):
    def test_uses_education_enabled_field_instead_of_nonexistent_status(self):
        columns = {"name", "enabled", "date_of_leaving"}
        self.assertTrue(
            _student_is_inactive(
                {"enabled": 0, "date_of_leaving": "2026-08-31"},
                columns,
                "2026-09-09",
            )
        )
        self.assertFalse(
            _student_is_inactive(
                {"enabled": 1, "date_of_leaving": None},
                columns,
                "2026-09-09",
            )
        )

    def test_future_leaving_date_remains_active_at_snapshot_date(self):
        self.assertFalse(
            _student_is_inactive(
                {"enabled": 0, "date_of_leaving": "2026-10-01"},
                {"enabled", "date_of_leaving"},
                "2026-09-09",
            )
        )

    def test_missing_enabled_column_does_not_invent_an_inactive_state(self):
        self.assertFalse(
            _student_is_inactive(
                {"status": "Disabled", "date_of_leaving": "2026-08-31"},
                {"status", "date_of_leaving"},
                "2026-09-09",
            )
        )
