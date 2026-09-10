frappe.ui.form.on('School Fund Request', {
    refresh(frm) {
        if (frm.is_new()) return;
        [
            ['payment_entry', 'Payment Entry'],
            ['journal_entry', 'Journal Entry'],
            ['purchase_invoice', 'Purchase Invoice']
        ].forEach(([fieldname, doctype]) => {
            if (!frm.doc[fieldname]) return;
            frm.add_custom_button(__(`Open ${doctype}`), () => {
                frappe.set_route('Form', doctype, frm.doc[fieldname]);
            });
        });
    }
});
