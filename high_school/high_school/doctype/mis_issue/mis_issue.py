# Copyright (c) 2026, Sione Hikaione Fonua Kata and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document
from frappe.utils import now_datetime

from high_school.high_school.mis.issues import (
    build_issue_key,
)


CLOSED_STATUSES = {
    "Resolved",
    "Dismissed",
}


class MISIssue(Document):

    def before_insert(self):
        """Set initial management metadata."""

        if not self.status:
            self.status = "Open"

        if not self.first_detected:
            self.first_detected = (
                now_datetime()
            )

        if not self.last_detected:
            self.last_detected = (
                self.first_detected
            )

        if not self.issue_key:

            self.issue_key = (
                build_issue_key(
                    source_type=self.source_type,
                    reference_doctype=(
                        self.reference_doctype
                    ),
                    reference_name=(
                        self.reference_name
                    ),
                    school_term=(
                        self.school_term
                    ),
                )
            )


    def validate(self):
        """Validate issue lifecycle."""

        previous = (
            self.get_doc_before_save()
        )

        previous_status = (
            previous.status
            if previous
            else None
        )

        # =================================================
        # Resolution
        # =================================================

        if (
            self.status
            in CLOSED_STATUSES
        ):

            if not self.resolution_type:

                frappe.throw(
                    "Resolution Type is required "
                    "before resolving or dismissing "
                    "an MIS Issue."
                )

            # Set resolution audit fields only when
            # transitioning into a closed state.
            if (
                previous_status
                not in CLOSED_STATUSES
            ):

                self.resolved_on = (
                    now_datetime()
                )

                self.resolved_by = (
                    frappe.session.user
                )

        # =================================================
        # Reopening
        # =================================================

        elif (
            previous_status
            in CLOSED_STATUSES
        ):

            self.resolved_on = None
            self.resolved_by = None

            self.resolution_type = None
            self.resolution_notes = None

            self.exclude_from_kpis = 0