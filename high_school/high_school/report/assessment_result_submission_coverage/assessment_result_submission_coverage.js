frappe.query_reports['Assessment Result Submission Coverage'] = {
	filters: [
		{ fieldname: 'examination_cycle', label: __('School Assessment Cycle'), fieldtype: 'Link', options: 'School Examination Cycle' },
		{ fieldname: 'assessment_type', label: __('Assessment Type'), fieldtype: 'Select', options: '\nExamination\nInternal Assessment' },
		{ fieldname: 'school_term', label: __('School Term'), fieldtype: 'Link', options: 'School Term' },
		{ fieldname: 'assessment_group', label: __('Assessment Group'), fieldtype: 'Link', options: 'Assessment Group' },
		{ fieldname: 'course', label: __('Course'), fieldtype: 'Link', options: 'Course' },
		{ fieldname: 'student_group', label: __('Student Group'), fieldtype: 'Link', options: 'Student Group' },
		{ fieldname: 'responsible_user', label: __('Teacher User'), fieldtype: 'Link', options: 'User' },
		{ fieldname: 'status', label: __('Status'), fieldtype: 'Select', options: '\nAwaiting Plan Submission\nInstructor Mapping Error\nAwaiting Assessment\nAwaiting Results\nMarking In Progress\nOverdue\nResults Complete\nPlan Cancelled' },
		{ fieldname: 'overdue_only', label: __('Overdue Only'), fieldtype: 'Check', default: 0 },
		{ fieldname: 'missing_results_only', label: __('Unresolved Results Only'), fieldtype: 'Check', default: 0 },
	],
};
