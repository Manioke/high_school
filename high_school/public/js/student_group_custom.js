frappe.ui.form.on('Student Group', {
    refresh(frm) {
        // Frappe v16 removed this private Page API. The standard Education
        // Get Students button is now routed server-side through hooks.py, so
        // this legacy override should only run on versions that still expose it.
        if (typeof frm.page.set_inner_btn_group_item !== 'function') return;
        frm.page.set_inner_btn_group_item(__('Get Students'), null, function() {
            frappe.call({
                method: 'high_school.high_school.api.get_students_custom',
                args: {
                    academic_year: frm.doc.academic_year,
                    group_based_on: frm.doc.group_based_on,
                    academic_term: frm.doc.academic_term,
                    course: frm.doc.course,
                    student_group: frm.doc.name,
                    student_group_name: frm.doc.student_group_name,
                    program: frm.doc.program,
                    batch: frm.doc.batch || frm.doc.student_batch_name || frm.doc.student_batch,
                    student_category: frm.doc.student_category,
                },
                freeze: true,
                callback(r) {
                    if (!r.message) return;
                    frm.set_value('students', []);
                    r.message.filter(row => Number(row.active === undefined ? 1 : row.active) !== 0).forEach(row => {
                        const student = frm.add_child('students');
                        student.student = row.student;
                        student.student_name = row.student_name;
                        student.active = 1;
                    });
                    frm.refresh_field('students');
                    frappe.show_alert({
                        message: __('{0} enabled students found', [frm.doc.students.length]),
                        indicator: 'green',
                    });
                },
            });
        });
    },
});
