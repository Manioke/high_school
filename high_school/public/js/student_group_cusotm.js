frappe.ui.form.on('Student Group', {
    refresh: function(frm) {
        // This forces our custom function onto the button
        frm.page.set_inner_btn_group_item(__('Get Students'), null, function() {
            frappe.call({
                method: "high_school.high_school.api.get_students_custom",
                args: {
                    "academic_year": frm.doc.academic_year,
                    "course": frm.doc.course,
                    "student_group": frm.doc.name, // The unique ID (e.g. F5-COM-Opt1-2026)
                    "student_group_name": frm.doc.student_group_name,
                    "program": frm.doc.program,
                    "batch": frm.doc.batch
                },
                freeze: true,
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('students', []);
                        r.message.forEach(d => {
                            let s = frm.add_child('students');
                            s.student = d.student;
                            s.student_name = d.student_name;
                            s.active = d.active;
                        });
                        frm.refresh_field('students');
                        frappe.show_alert({
                            message: __("{0} students found for this Option slot", [r.message.length]), 
                            indicator: 'green'
                        });
                    }
                }
            });
        });
    }
});