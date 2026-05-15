frappe.ui.form.on('Program Enrollment', {
    refresh: function(frm) {
        // Hide the manual fee table because our back-end script handles the logic
        frm.set_df_property('fees', 'hidden', 1);
    }
});