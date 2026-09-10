frappe.ui.form.on('Student Intervention Plan', {
    refresh(frm) {
        if (frm.is_new()) return;

        if (frm.doc.status === 'Diagnosis Required') {
            frm.add_custom_button(__('Start Action Plan'), () => {
                frm.set_value('status', 'Action Planned');
                frm.scroll_to_field('root_cause');
            });
        }

        if (['Action Planned', 'Overdue'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Begin Intervention'), () => frm.set_value('status', 'In Progress'));
        }

        if (frm.doc.status === 'In Progress') {
            frm.add_custom_button(__('Ready for Follow-up'), () => {
                frm.set_value('status', 'Ready for Review');
                frm.scroll_to_field('follow_up_value');
            });
        }

        if (!['Closed - Successful', 'Closed - Not Required'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Escalate'), () => frm.set_value('status', 'Escalated'));
        }

        if (['Ready for Review', 'Escalated'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Close as Successful'), () => {
                frm.set_value('status', 'Closed - Successful');
                frm.scroll_to_field('follow_up_value');
            }, __('Close'));
            frm.add_custom_button(__('Close as Not Required'), () => {
                frm.set_value('status', 'Closed - Not Required');
                frm.scroll_to_field('resolution_notes');
            }, __('Close'));
        }
    },
});
