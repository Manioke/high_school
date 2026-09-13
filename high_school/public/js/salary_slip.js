frappe.ui.form.on('Salary Slip', {
    refresh(frm) {
        if (frm.is_new()) return;
        frappe.db.get_single_value('School MIS Settings', 'salary_slip_print_format').then((format) => {
            if (!format) return;
            frm.add_custom_button(__('Print School Salary Slip'), () => {
                frappe.utils.print(frm.doctype, frm.docname, format, frm.doc.letter_head || null, frm.doc.language || null);
            }, __('School Print'));
        });
        frm.add_custom_button(__('Customize Salary Slip Template'), () => {
            frappe.set_route('List', 'Print Format', { doc_type: 'Salary Slip' });
        }, __('School Print'));
    }
});
