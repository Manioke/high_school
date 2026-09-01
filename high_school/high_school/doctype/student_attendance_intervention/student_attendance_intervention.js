frappe.ui.form.on('Student Attendance Intervention', {
    refresh(frm) {
        if (frm.is_new()) return;

        if (!['Resolved', 'Dismissed'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Schedule Meeting'), () => {
                frm.set_value('status', 'Meeting Scheduled');
                frm.scroll_to_field('meeting_date');
            });
        }

        if (frm.doc.status !== 'Resolved') {
            frm.add_custom_button(__('Resolve Follow-up'), () => {
                frm.set_value('status', 'Resolved');
                frm.scroll_to_field('resolution_notes');
            });
        }
    },
});

