frappe.query_reports['Assessment Plan Exam Timetable'] = {
	filters: [
		{
			fieldname: 'academic_year',
			label: __('Academic Year'),
			fieldtype: 'Link',
			options: 'Academic Year',
			reqd: 1,
		},
		{
			fieldname: 'assessment_group',
			label: __('Assessment Group'),
			fieldtype: 'Link',
			options: 'Assessment Group',
			reqd: 1,
		},
		{ fieldname: 'program', label: __('Program'), fieldtype: 'Link', options: 'Program', reqd: 1 },
		{ fieldname: 'student_batch', label: __('Student Batch'), fieldtype: 'Link', options: 'Student Batch Name', get_query: () => ({ filters: { custom_program: frappe.query_report.get_filter_value('program') } }) },
		{ fieldname: 'student_group', label: __('Student Group'), fieldtype: 'Link', options: 'Student Group' },
		{
			fieldname: 'from_date',
			label: __('From Date'),
			fieldtype: 'Date',
			description: __('Leave both dates blank to use the complete scheduled examination period.'),
		},
		{
			fieldname: 'to_date',
			label: __('To Date'),
			fieldtype: 'Date',
			description: __('Enter only one date to create a 14-day timetable window.'),
		},
		{
			fieldname: 'display_by',
			label: __('Display By'),
			fieldtype: 'Select',
			options: 'Course\nStudent Group',
			default: 'Course',
			reqd: 1,
		},
		{
			fieldname: 'include_draft',
			label: __('Include Draft Plans'),
			fieldtype: 'Check',
			default: 1,
		},
	],
};
