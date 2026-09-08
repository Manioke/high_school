frappe.ui.form.on('School Fund Request', {
    refresh(frm) {
        if (frm.is_new()) return;

        if (frm.doc.payment_entry) {
            frm.add_custom_button(__('Open Payment Entry'), () => {
                frappe.set_route('Form', 'Payment Entry', frm.doc.payment_entry);
            });
        }
        if (frm.doc.journal_entry) {
            frm.add_custom_button(__('Open Journal Entry'), () => {
                frappe.set_route('Form', 'Journal Entry', frm.doc.journal_entry);
            });
        }
        if (frm.doc.purchase_invoice) {
            frm.add_custom_button(__('Open Purchase Invoice'), () => {
                frappe.set_route('Form', 'Purchase Invoice', frm.doc.purchase_invoice);
            });
        }
    }
});
