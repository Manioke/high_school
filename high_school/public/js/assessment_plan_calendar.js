frappe.views.calendar['Assessment Plan'] = {
	field_map: {
		start: 'schedule_date',
		end: 'schedule_date',
		id: 'name',
		title: 'assessment_name',
		allDay: 1,
	},
	get_events_method: 'frappe.desk.calendar.get_events',
};
