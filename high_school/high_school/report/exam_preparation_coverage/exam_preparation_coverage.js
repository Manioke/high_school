frappe.query_reports['Exam Preparation Coverage'] = {
	filters: [
		{
			fieldname: 'examination_cycle',
			label: __('Examination Cycle'),
			fieldtype: 'Link',
			options: 'School Examination Cycle',
		},
		{
			fieldname: 'status',
			label: __('Status'),
			fieldtype: 'Select',
			options: '\nAwaiting Assignment\nAssigned\nIn Preparation\nSubmitted to HOD\nChanges Requested\nSubmitted to Exam Administration\nApproved\nPlans Partially Created\nComplete',
		},
		{
			fieldname: 'department',
			label: __('Department'),
			fieldtype: 'Link',
			options: 'Department',
		},
		{
			fieldname: 'student_batch',
			label: __('Student Batch'),
			fieldtype: 'Link',
			options: 'Student Batch Name',
		},
		{
			fieldname: 'lead_teacher_user',
			label: __('Lead Teacher'),
			fieldtype: 'Link',
			options: 'User',
		},
		{
			fieldname: 'overdue_only',
			label: __('Overdue Only'),
			fieldtype: 'Check',
		},
		{
			fieldname: 'missing_plans_only',
			label: __('Missing Assessment Plans Only'),
			fieldtype: 'Check',
		},
	],
};
