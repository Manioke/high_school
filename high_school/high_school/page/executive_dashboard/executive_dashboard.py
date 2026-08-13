import frappe
def before_naming(self):
    year = frappe.db.get_value(
        "Academic Year",
        self.academic_year,
        "name"
    )

    term_number = {
        "Term 1": "1",
        "Term 2": "2",
        "Term 3": "3",
        "Term 4": "4"
    }.get(self.term)

    self.name = f"{year}-Term{term_number}"