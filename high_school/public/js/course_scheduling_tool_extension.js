// This adds logic to the existing DocType without modifying the original file
frappe.ui.form.on('Course Scheduling Tool', {
    refresh: function(frm) {
        // Hide the original time fields via CSS/JS so it's portable
        frm.set_df_property('from_time', 'hidden', 1);
        frm.set_df_property('to_time', 'hidden', 1);
        
        // Change the labels of the original fields if needed
        frm.set_df_property('custom_period', 'reqd', 1);
        frappe.db.get_single_value('School MIS Settings', 'require_rooms_for_timetable').then((required) => {
            if (frm.fields_dict.room) frm.set_df_property('room', 'reqd', Number(required || 0) === 1);
        });
    },
    
    custom_period: function(frm) {
        if (frm.doc.custom_period) {
            frappe.db.get_value('School Period', frm.doc.custom_period, ['from_time', 'to_time'], (r) => {
                if (r) {
                    frm.set_value('from_time', normalise_school_time(r.from_time));
                    frm.set_value('to_time', normalise_school_time(r.to_time));
                }
            });
        }
    }
});

function normalise_school_time(value) {
    const parts = String(value || '').split(':');
    if (parts.length < 2) return value;
    return [parts[0].padStart(2, '0'), parts[1].padStart(2, '0'), (parts[2] || '00').padStart(2, '0')].join(':');
}
