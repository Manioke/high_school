import frappe
from frappe.model.document import Document

class TaliuiAkonofo(Document):
    def validate(self):
        # 1. Set the punishment hours logic
        # You can change this '3' to any number you want here
        punishment_rate = 2 

        if self.status == "Absent":
            self.houa_ngaue_moua = punishment_rate
        else:
            # If they are present or on leave, they shouldn't get hours
            self.houa_ngaue_moua = 0

    def on_update(self):
        # 2. Every time a record is saved/updated, update the Student's total
        self.update_student_total_moua()

    def on_trash(self):
        # 3. If a record is deleted, recalculate total
        self.update_student_total_moua()

    def update_student_total_moua(self):
        if not self.student:
            return
            
        # Sum all hours for this student from the Taliui Akonofo table
        total = frappe.db.sql("""
            SELECT SUM(houa_ngaue_moua) 
            FROM `tabTaliui Akonofo` 
            WHERE student = %s
        """, self.student)[0][0] or 0
        
        # Update the Student DocType custom field
        frappe.db.set_value("Student", self.student, "custom_total_moua", total, update_modified=False)