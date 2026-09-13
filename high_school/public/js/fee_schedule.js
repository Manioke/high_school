frappe.ui.form.on('Fee Schedule', {
    setup(frm) {
        frm.set_query('custom_school_term', () => ({
            filters: { academic_year: frm.doc.academic_year },
        }));
    },
    academic_year(frm) {
        if (frm.doc.custom_school_term) {
            frappe.db.get_value('School Term', frm.doc.custom_school_term, 'academic_year')
                .then((r) => {
                    if (r.message?.academic_year !== frm.doc.academic_year) {
                        frm.set_value('custom_school_term', '');
                    }
                });
        }
    },
});
