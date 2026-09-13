frappe.ui.form.on('Student Applicant', {
    setup(frm) {
        frm.set_query('custom_student_batch_name', () => ({
            filters: { custom_program: frm.doc.program },
        }));
    },
    program(frm) {
        if (frm.doc.custom_student_batch_name) {
            frappe.db.get_value('Student Batch Name', frm.doc.custom_student_batch_name, 'custom_program')
                .then((r) => {
                    if (r.message?.custom_program !== frm.doc.program) {
                        frm.set_value('custom_student_batch_name', '');
                    }
                });
        }
    },
});
