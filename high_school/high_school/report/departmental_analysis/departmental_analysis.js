frappe.query_reports['Departmental Analysis'] = {
    filters: [
        { fieldname: 'academic_year', label: __('Academic Year'), fieldtype: 'Link', options: 'Academic Year', reqd: 1 },
        { fieldname: 'school_term', label: __('School Term'), fieldtype: 'Link', options: 'School Term', get_query: () => ({ filters: { academic_year: frappe.query_report.get_filter_value('academic_year') } }) },
        { fieldname: 'program', label: __('Program'), fieldtype: 'Link', options: 'Program', reqd: 1 },
        { fieldname: 'department', label: __('Department'), fieldtype: 'Link', options: 'Department' },
        { fieldname: 'student_batch', label: __('Student Batch'), fieldtype: 'Link', options: 'Student Batch Name', get_query: () => ({ filters: { custom_program: frappe.query_report.get_filter_value('program') } }) },
        { fieldname: 'student_group', label: __('Student Group / Stream'), fieldtype: 'Link', options: 'Student Group' },
        { fieldname: 'grading_scale', label: __('Grading Scale for Average'), fieldtype: 'Link', options: 'Grading Scale' },
    ],
};
