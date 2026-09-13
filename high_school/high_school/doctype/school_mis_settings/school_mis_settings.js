// Copyright (c) 2026, Sione Hikaione Fonua Kata and contributors
// For license information, please see license.txt

frappe.ui.form.on('School MIS Settings', {
    setup(frm) {
        frm.set_query('student_report_card_print_format', () => ({ filters: { doc_type: 'Student Performance Summary' } }));
        frm.set_query('salary_slip_print_format', () => ({ filters: { doc_type: 'Salary Slip' } }));
    },
    refresh(frm) {
        frm.add_custom_button(__('Customize Report Card'), () => frappe.set_route('List', 'Print Format', { doc_type: 'Student Performance Summary' }), __('Print Templates'));
        frm.add_custom_button(__('Customize Salary Slip'), () => frappe.set_route('List', 'Print Format', { doc_type: 'Salary Slip' }), __('Print Templates'));
    }
});
