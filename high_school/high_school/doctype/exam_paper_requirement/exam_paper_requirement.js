frappe.ui.form.on('Exam Paper Requirement', {
	setup(frm) {
		const user_filter = () => ({ filters: { enabled: 1, user_type: 'System User' } });
		frm.set_query('hod_user', user_filter);
		frm.set_query('lead_teacher_user', user_filter);
		frm.set_query('user', 'collaborators', user_filter);
	},

	refresh(frm) {
		const roles = new Set(frappe.user_roles || []);
		const is_manager = roles.has('System Manager') || roles.has('Education Manager');
		const is_hod = is_manager || frappe.session.user === frm.doc.hod_user;
		const collaborators = (frm.doc.collaborators || []).map((row) => row.user);
		const is_teacher = is_manager || frappe.session.user === frm.doc.lead_teacher_user || collaborators.includes(frappe.session.user);
		for (const fieldname of ['examination_date', 'from_time', 'to_time', 'room', 'grading_scale']) {
			frm.set_df_property(fieldname, 'read_only', !is_manager);
		}

		if (!frm.is_new() && is_teacher && ['Assigned', 'In Preparation', 'Changes Requested'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Submit to HOD'), () => {
				frappe.confirm(__('Submit revision {0} to the HOD?', [(frm.doc.revision_number || 0) + 1]), () => {
					frm.call('submit_to_hod').then(() => frm.reload_doc());
				});
			}, __('Paper Workflow'));
		}

		if (!frm.is_new() && is_hod && frm.doc.status === 'Submitted to HOD') {
			frm.add_custom_button(__('Approve and Send to Exam Admin'), () => {
				frm.call('approve_by_hod').then(() => frm.reload_doc());
			}, __('Paper Workflow'));
			add_request_changes_button(frm);
		}

		if (!frm.is_new() && is_manager && frm.doc.status === 'Submitted to Exam Administration') {
			frm.add_custom_button(__('Final Approval'), () => {
				frm.call('approve_by_admin').then(() => frm.reload_doc());
			}, __('Paper Workflow'));
			add_request_changes_button(frm);
		}

		if (!frm.is_new() && is_manager && ['Approved', 'Plans Partially Created', 'Complete'].includes(frm.doc.status)) {
			frm.add_custom_button(__('Create / Check Assessment Plans'), () => {
				frappe.route_options = {
					academic_year: frm.doc.academic_year,
					school_term: frm.doc.school_term,
					assessment_group: frm.doc.assessment_group,
					course: frm.doc.course,
					student_batch: frm.doc.student_batch,
					exam_paper_requirement: frm.doc.name,
				};
				frappe.set_route('school-assessment-plan-setup');
			}, __('Assessment Plans'));
		}

		if (!frm.is_new() && is_hod) {
			frm.add_custom_button(__('Send Reminder'), () => {
				frm.call('send_manual_reminder').then(() => {
					frappe.show_alert({ message: __('Reminder sent'), indicator: 'green' });
					frm.reload_doc();
				});
			}, __('Paper Workflow'));

			frm.add_custom_button(__('Refresh Plan Coverage'), () => {
				frm.call('refresh_plan_coverage').then(() => frm.reload_doc());
			}, __('Assessment Plans'));
		}
	},
});

function add_request_changes_button(frm) {
	frm.add_custom_button(__('Request Changes'), () => {
		frappe.prompt(
			[{ fieldname: 'notes', fieldtype: 'Small Text', label: __('Changes Required'), reqd: 1 }],
			(values) => frm.call('request_changes', { notes: values.notes }).then(() => frm.reload_doc()),
			__('Request Paper Changes'),
			__('Send Back'),
		);
	}, __('Paper Workflow'));
}
