function populate_from_returning_student(frm) {
    if (frm.doc.custom_application_type !== 'Old Student' || !frm.doc.custom_student_id) {
        return;
    }

    const preserved = {
        custom_application_type: frm.doc.custom_application_type,
        custom_student_id: frm.doc.custom_student_id,
        academic_year: frm.doc.academic_year,
        academic_term: frm.doc.academic_term,
        application_status: frm.doc.application_status,
    };
    const protected_fields = new Set([
        'name', 'doctype', 'owner', 'creation', 'modified', 'modified_by',
        'docstatus', 'idx', 'enabled', 'status', 'title', 'student_name',
        'custom_application_type', 'custom_student_id', 'academic_year',
        'academic_term', 'application_status', 'courses',
    ]);

    frappe.db.get_doc('Student', frm.doc.custom_student_id).then(student => {
        const values = {};
        (frm.meta.fields || []).forEach(field => {
            if (!field.fieldname || protected_fields.has(field.fieldname)) return;
            if (['Table', 'Table MultiSelect', 'Section Break', 'Column Break', 'Tab Break', 'Button', 'HTML'].includes(field.fieldtype)) return;
            if (student[field.fieldname] !== undefined && student[field.fieldname] !== null) {
                values[field.fieldname] = student[field.fieldname];
            }
        });

        const email = student.student_email_id || student.student_email ||
            student.student_email_address || student.email || student.user;
        ['student_email_id', 'student_email', 'student_email_address'].forEach(fieldname => {
            if (email && frm.fields_dict[fieldname]) values[fieldname] = email;
        });

        if (frm.fields_dict.first_name) {
            values.first_name = student.first_name || values.first_name || student.student_name;
        }
        if (frm.fields_dict.middle_name && student.middle_name) values.middle_name = student.middle_name;
        if (frm.fields_dict.last_name && student.last_name) values.last_name = student.last_name;

        Object.assign(values, preserved);
        return frm.set_value(values);
    }).then(() => {
        frappe.show_alert({
            message: __('Returning Student details loaded. The selected Academic Year and Term were preserved.'),
            indicator: 'green',
        });
    });
}

frappe.ui.form.on('Student Applicant', {
    custom_student_id(frm) {
        populate_from_returning_student(frm);
    },

    custom_application_type(frm) {
        if (frm.doc.custom_application_type === 'New Student') {
            frm.set_value('custom_student_id', '');
        } else {
            populate_from_returning_student(frm);
        }
    },
});
