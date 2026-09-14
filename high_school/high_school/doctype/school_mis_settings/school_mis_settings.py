# Copyright (c) 2026, Sione Hikaione Fonua Kata and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class SchoolMISSettings(Document):
	def validate(self):
		# A school without fee master data must still be installable/migratable.
		if not cint(self.get("enable_automatic_late_registration_fees")):
			return
		structure = self.get("late_registration_fee_structure")
		if not structure:
			frappe.throw(_("Select a submitted Late Registration Fee Structure before enabling automatic late fees."))
		if frappe.db.get_value("Fee Structure", structure, "docstatus") != 1:
			frappe.throw(_("Late Registration Fee Structure {0} must exist and be submitted.").format(structure))
