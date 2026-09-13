frappe.query_reports['School Course Timetable'] = {
    filters: [
        { fieldname: 'academic_year', label: __('Academic Year'), fieldtype: 'Link', options: 'Academic Year', reqd: 1 },
        { fieldname: 'school_term', label: __('School Term'), fieldtype: 'Link', options: 'School Term', reqd: 1, get_query: () => ({ filters: { academic_year: frappe.query_report.get_filter_value('academic_year') } }) },
        { fieldname: 'program', label: __('Program'), fieldtype: 'Link', options: 'Program', reqd: 1 },
        { fieldname: 'week_start', label: __('Week Starting'), fieldtype: 'Date', description: __('Any date in the required teaching week.') },
        { fieldname: 'student_batch', label: __('Student Batch'), fieldtype: 'Link', options: 'Student Batch Name', get_query: () => ({ filters: { custom_program: frappe.query_report.get_filter_value('program') } }) },
        { fieldname: 'student_group', label: __('Student Group'), fieldtype: 'Link', options: 'Student Group' },
        { fieldname: 'instructor', label: __('Instructor'), fieldtype: 'Link', options: 'Instructor' },
    ],
};
