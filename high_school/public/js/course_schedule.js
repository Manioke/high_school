frappe.ui.form.on('Course Schedule', {
    refresh(frm) {
        frappe.db.get_single_value('School MIS Settings', 'require_rooms_for_timetable').then((required) => {
            if (frm.fields_dict.room) frm.set_df_property('room', 'reqd', Number(required || 0) === 1);
        });
    },
    custom_period(frm) {
        if (!frm.doc.custom_period) return;
        frappe.db.get_value('School Period', frm.doc.custom_period, ['from_time', 'to_time']).then((r) => {
            const values = r.message || {};
            if (values.from_time) frm.set_value('from_time', values.from_time);
            if (values.to_time) frm.set_value('to_time', values.to_time);
        });
    }
});
