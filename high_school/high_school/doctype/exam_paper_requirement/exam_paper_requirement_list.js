frappe.listview_settings['Exam Paper Requirement'] = {
	add_fields: ['status', 'paper_submission_deadline', 'missing_plan_count'],
	get_indicator(doc) {
		const colours = {
			'Awaiting Assignment': 'gray',
			'Assigned': 'blue',
			'In Preparation': 'blue',
			'Submitted to HOD': 'orange',
			'Changes Requested': 'red',
			'Submitted to Exam Administration': 'orange',
			'Approved': 'green',
			'Plans Partially Created': 'yellow',
			'Complete': 'green',
		};
		return [__(doc.status), colours[doc.status] || 'gray', `status,=,${doc.status}`];
	},
};
