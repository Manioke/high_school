frappe.ui.form.on('Assessment Plan', {
	refresh(frm) {
		const roles = new Set(frappe.user_roles || []);
		if (!roles.has('Education Manager') && !roles.has('System Manager')) return;

		frm.add_custom_button(__('Open Exam Timetable'), () => {
			frappe.route_options = {
				academic_year: frm.doc.academic_year,
				assessment_group: frm.doc.assessment_group,
			};
			frappe.set_route('query-report', 'Assessment Plan Exam Timetable');
		}, __('Print'));
	},
});
