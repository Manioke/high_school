frappe.ui.form.on('Program Enrollment Tool', {
    refresh: function(frm) {
        // Unlock row field inputs in the grid layout view dynamically!
        frm.fields_dict['students'].grid.get_field('student_category').read_only = 0;
        frm.fields_dict['students'].grid.get_field('student_batch_name').read_only = 0;
        frm.fields_dict['students'].grid.refresh();
    }
});

// Row grid behavior actions
frappe.ui.form.on('Program Enrollment Tool Student', {
    form_render: function(frm, cdt, cdn) {
        // Double check field protection clearance on open
        let row = frappe.get_doc(cdt, cdn);
        let grid_row = frm.fields_dict['students'].grid.get_row(cdn);
        if(grid_row) {
            grid_row.get_field('student_category').toggle_editable(true);
            grid_row.get_field('student_batch_name').toggle_editable(true);
        }
    }
});