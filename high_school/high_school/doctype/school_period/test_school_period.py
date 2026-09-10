# Copyright (c) 2026, Sione Hikaione Fonua Kata and Contributors
# See license.txt

from datetime import time, timedelta

from frappe.tests import IntegrationTestCase

from high_school.high_school.course_scheduling import normalise_time


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestSchoolPeriod(IntegrationTestCase):
	"""
	Integration tests for SchoolPeriod.
	Use this class for testing interactions between multiple components.
	"""

	def test_normalise_time_zero_pads_single_digit_hour(self):
		self.assertEqual(normalise_time("9:50:00"), "09:50:00")

	def test_normalise_time_accepts_frappe_time_values(self):
		self.assertEqual(normalise_time(time(9, 50)), "09:50:00")
		self.assertEqual(normalise_time(timedelta(hours=10, minutes=40)), "10:40:00")
