from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from high_school.high_school.mis.school_finance import _reporting_date


class TestSchoolFinanceReportingDate(TestCase):
    def test_current_term_reports_through_today(self):
        term = SimpleNamespace(start_date="2026-09-01", end_date="2026-09-30")
        with patch(
            "high_school.high_school.mis.school_finance.nowdate",
            return_value="2026-09-09",
        ):
            as_of, basis = _reporting_date(term)
        self.assertEqual(str(as_of), "2026-09-09")
        self.assertEqual(basis, "current_term")

    def test_closed_term_reports_through_term_end(self):
        term = SimpleNamespace(start_date="2026-08-01", end_date="2026-08-31")
        with patch(
            "high_school.high_school.mis.school_finance.nowdate",
            return_value="2026-09-09",
        ):
            as_of, basis = _reporting_date(term)
        self.assertEqual(str(as_of), "2026-08-31")
        self.assertEqual(basis, "closed_term")

    def test_future_demo_term_never_creates_a_reversed_range(self):
        term = SimpleNamespace(start_date="2026-09-14", end_date="2026-10-09")
        with patch(
            "high_school.high_school.mis.school_finance.nowdate",
            return_value="2026-09-09",
        ):
            as_of, basis = _reporting_date(term)
        self.assertEqual(str(as_of), "2026-10-09")
        self.assertEqual(basis, "future_term_preview")
        self.assertGreaterEqual(str(as_of), term.start_date)
