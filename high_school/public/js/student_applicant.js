// In public/js/student_applicant.js

frappe.ui.form.on('Student Applicant', {
    custom_student_id: function(frm) {
        if (frm.doc.custom_application_type === 'Old Student' && frm.doc.custom_student_id) {
            
            // 1. Lock in the current Academic Year and Term entered on the form
            const current_academic_year = frm.doc.academic_year;
            const current_academic_term = frm.doc.academic_term;
            
            // 2. Fetch the FULL master Student document details
            frappe.db.get_doc('Student', frm.doc.custom_student_id)
                .then(student_doc => {
                    if (student_doc) {
                        
                        // 3. Define fields that must NOT be auto-filled from the master student record
                        const fields_to_skip = [
                            'student_email_id', 
                            'student_email_address',
                            'academic_year',
                            'academic_term'
                        ];
                        
                        // 4. Clear any bulk child tables to speed up form injection
                        frm.doc.courses = []; 
                        
                        // 5. Automatically map all fields that share the exact same name
                        let applicant_fields = frm.meta.fields.map(f => f.fieldname);
                        
                        applicant_fields.forEach(fieldname => {
                            if (student_doc[fieldname] !== undefined && 
                                student_doc[fieldname] !== null && 
                                !fields_to_skip.includes(fieldname)) {
                                
                                frm.set_value(fieldname, student_doc[fieldname]);
                            }
                        });

                        // 6. Handle the Name Split Edge Case:
                        if (student_doc.student_name) {
                            frm.set_value('first_name', student_doc.student_name);
                        }

                        // 7. Force-restore the new Academic Year and Term 
                        // This overrides any framework-level mapping that happened in the background
                        if (current_academic_year) {
                            frm.set_value('academic_year', current_academic_year);
                        }
                        if (current_academic_term) {
                            frm.set_value('academic_term', current_academic_term);
                        }

                        frappe.show_alert({
                            message: __('Imported matching records. Target Academic Year preserved.'),
                            indicator: 'green'
                        });
                    }
                });
        }
    },
    custom_application_type: function(frm) {
        if (frm.doc.custom_application_type === 'New Student') {
            frm.set_value('custom_student_id', '');
        }
    }
});