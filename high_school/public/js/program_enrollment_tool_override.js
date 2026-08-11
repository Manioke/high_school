frappe.ui.form.on('Program Enrollment Tool', {
    refresh: function(frm) {
        // Unlock row fields in grid view
        if (frm.fields_dict['students'] && frm.fields_dict['students'].grid) {
            let grid = frm.fields_dict['students'].grid;
            
            if (grid.get_field('student_category')) {
                grid.get_field('student_category').read_only = 0;
            }
            if (grid.get_field('student_batch_name')) {
                grid.get_field('student_batch_name').read_only = 0;
            }
            grid.refresh();
        }

        // Add custom bulk action button to set Category/Batch for all loaded rows
        if (frm.doc.students && frm.doc.students.length > 0) {
            frm.add_custom_button(__('Set Mass Batch & Category'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Apply Batch & Category to All Rows'),
                    fields: [
                        {
                            label: 'Student Category',
                            fieldname: 'student_category',
                            fieldtype: 'Link',
                            options: 'Student Category'
                        },
                        {
                            label: 'Student Batch',
                            fieldname: 'student_batch_name',
                            fieldtype: 'Link',
                            options: 'Student Batch'
                        }
                    ],
                    primary_action_label: __('Apply to Rows'),
                    primary_action(values) {
                        (frm.doc.students || []).forEach(row => {
                            if (values.student_category) {
                                frappe.model.set_value(row.doctype, row.name, 'student_category', values.student_category);
                            }
                            if (values.student_batch_name) {
                                frappe.model.set_value(row.doctype, row.name, 'student_batch_name', values.student_batch_name);
                            }
                        });
                        frm.refresh_field('students');
                        d.hide();
                        frappe.show_alert({ message: __('Updated all rows successfully'), indicator: 'green' });
                    }
                });
                d.show();
            }, __('Actions'));
        }
    }
});

// Row-level events
frappe.ui.form.on('Program Enrollment Tool Student', {
    form_render: function(frm, cdt, cdn) {
        let grid_row = frm.fields_dict['students'].grid.get_row(cdn);
        if (grid_row) {
            if (grid_row.get_field('student_category')) {
                grid_row.get_field('student_category').toggle_editable(true);
            }
            if (grid_row.get_field('student_batch_name')) {
                grid_row.get_field('student_batch_name').toggle_editable(true);
            }
        }
    }
});