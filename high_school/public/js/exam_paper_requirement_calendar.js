frappe.views.calendar['Exam Paper Requirement'] = {
	field_map: {
		start: 'paper_submission_deadline',
		end: 'paper_submission_deadline',
		id: 'name',
		title: 'requirement_title',
		status: 'status',
		allDay: 1,
	},
	style_map: {
		'Awaiting Assignment': 'gray',
		'Assigned': 'blue',
		'In Preparation': 'blue',
		'Submitted to HOD': 'orange',
		'Changes Requested': 'red',
		'Submitted to Exam Administration': 'orange',
		'Approved': 'green',
		'Plans Partially Created': 'yellow',
		'Complete': 'green',
	},
	get_events_method: 'frappe.desk.calendar.get_events',
};
