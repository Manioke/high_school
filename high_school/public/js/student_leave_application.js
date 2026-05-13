frappe.ui.form.on('Student Leave Application', {
    refresh: function(frm) {
        // Hide the fields we don't want the user to touch
        frm.set_df_property('attendance_based_on', 'hidden', 1);
        frm.set_df_property('student_group', 'hidden', 1);
        frm.set_df_property('course_schedule', 'hidden', 1);
        
        // Remove mandatory status
        frm.set_df_property('attendance_based_on', 'reqd', 0);
        frm.set_df_property('student_group', 'reqd', 0);
    },
    student: function(frm) {
        // Wait for the core Education app to finish its 'student' trigger logic
        setTimeout(() => {
            frm.set_df_property('student_group', 'reqd', 0);
            frm.set_df_property('course_schedule', 'reqd', 0);
            frm.set_df_property('attendance_based_on', 'reqd', 0);
        }, 1200); // 1.2 second delay to ensure it runs LAST
    }
});