frappe.ui.form.on('School Timetable Generator', {
    setup(frm) {
        frm.set_query('school_term', () => ({ filters: { academic_year: frm.doc.academic_year } }));
        frm.set_query('student_batch', () => ({ filters: { custom_program: frm.doc.program } }));
        frm.set_query('student_group', 'courses', () => ({ filters: { academic_year: frm.doc.academic_year, program: frm.doc.program } }));
    },
    refresh(frm) {
        frappe.db.get_single_value('School MIS Settings', 'require_rooms_for_timetable').then((required) => {
            const grid = frm.fields_dict.courses && frm.fields_dict.courses.grid;
            if (grid) grid.update_docfield_property('room', 'reqd', Number(required || 0) === 1);
        });
        if (frm.is_new()) return;
        frm.add_custom_button(__('Load / Refresh Courses'), () => {
            frappe.confirm(__('Replace the current course rows with courses detected from the selected Student Groups and Programs?'), () => {
                frm.call('load_courses').then((r) => {
                    frm.reload_doc();
                    frappe.show_alert({ message: __('Loaded {0} timetable row(s).', [r.message.loaded]), indicator: 'green' });
                });
            });
        });
        frm.add_custom_button(__('Generate Course Schedules'), () => {
            frappe.confirm(__('Generate conflict-checked Course Schedule records for every teaching week in this School Term? Existing identical schedules will be kept.'), () => {
                frappe.dom.freeze(__('Saving and building the timetable...'));
                frm.save()
                    .then(() => frm.call('generate_schedules'))
                    .then((r) => {
                        const result = r.message || {};
                        frappe.msgprint(__('Created {0} schedule(s) across {1} week(s); {2} identical schedule(s) already existed.', [(result.created || []).length, result.weeks || 0, (result.skipped || []).length]));
                        return frm.reload_doc();
                    })
                    .finally(() => frappe.dom.unfreeze());
            });
        }, __('Actions'));
        frm.add_custom_button(__('Open Course Schedules'), () => frappe.set_route('List', 'Course Schedule', { custom_timetable_generator: frm.doc.name }), __('View'));
        frm.add_custom_button(__('Print Weekly Timetable'), () => frappe.set_route('query-report', 'School Course Timetable', {
            academic_year: frm.doc.academic_year,
            school_term: frm.doc.school_term,
            program: frm.doc.program,
            student_batch: frm.doc.student_batch || undefined,
        }), __('View'));
    }
});
