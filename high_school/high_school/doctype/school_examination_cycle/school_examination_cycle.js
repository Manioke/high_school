frappe.ui.form.on('School Examination Cycle', {
	setup(frm) {
		frm.set_query('hod_user', 'hod_assignments', () => ({
			filters: { enabled: 1, user_type: 'System User' },
		}));
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.status !== 'Closed') {
			frm.add_custom_button(__('Generate / Refresh Paper Requirements'), () => {
				frappe.confirm(
					__('Generate missing requirements and refresh their affected Student Groups? Existing teacher submissions will be preserved.'),
					() => frm.call('generate_requirements').then((r) => {
						const result = r.message || {};
						frappe.msgprint(__('Created {0}, refreshed {1}, and found {2} requirement(s) with no Student Group mapping.', [
							result.created || 0,
							result.updated || 0,
							result.without_groups || 0,
						]));
						frm.reload_doc();
					}),
			);
		}, __('Examination Preparation'));

			frm.add_custom_button(__('Preparation Coverage'), () => {
				frappe.set_route('query-report', 'Exam Preparation Coverage', {
					examination_cycle: frm.doc.name,
				});
			}, __('View'));

			frm.add_custom_button(__('Generate / Refresh Result Trackers'), () => {
				frappe.confirm(
					__('Create or refresh result-submission tracking for every Assessment Plan in this cycle?'),
					() => frm.call('generate_result_trackers').then((r) => {
						const result = r.message || {};
						frappe.msgprint(__('Created {0}, refreshed {1}, skipped {2}, and found {3} plan(s) with an instructor mapping problem.', [
							result.created || 0,
							result.updated || 0,
							result.skipped || 0,
							result.mapping_issues || 0,
						]));
					}),
				);
			}, __('Result Submission'));

			frm.add_custom_button(__('Result Submission Coverage'), () => {
				frappe.set_route('query-report', 'Assessment Result Submission Coverage', {
					examination_cycle: frm.doc.name,
				});
			}, __('View'));
		}
	},
});
