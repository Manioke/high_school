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
            frm.add_custom_button(__('Start Monitoring'), () => {
                frm.set_value('status', 'Monitoring');
            });
        }

        if (!['Closed - Successful', 'Closed - Not Required'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Escalate'), () => {
                frappe.prompt(
                    {
                        fieldname: 'reason',
                        fieldtype: 'Small Text',
                        label: __('Escalation Reason'),
                        reqd: 1
                    },
                    values => {
                        frappe.call({
                            method: 'high_school.high_school.student_interventions.escalate_intervention_plan',
                            args: {plan_name: frm.doc.name, reason: values.reason},
                            freeze: true,
                            freeze_message: __('Escalating intervention...'),
                            callback: () => frm.reload_doc()
                        });
                    },
                    __('Escalate Student Intervention'),
                    __('Escalate')
                );
            });
        }

        if (['Diagnosis Required', 'Action Planned', 'In Progress', 'Monitoring', 'Ready for Review', 'Escalated'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Close as Not Required'), () => {
                frm.set_value('status', 'Closed - Not Required');
                frm.scroll_to_field('resolution_notes');
            }, __('Close'));
        }
    },
});
