frappe.ui.form.on('Assessment Result Submission Tracker', {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__('Refresh Coverage'), () => {
			frm.call('refresh_coverage').then(() => frm.reload_doc());
		});

		if (frm.doc.assessment_plan) {
			frm.add_custom_button(__('Open Assessment Plan'), () => {
				frappe.set_route('Form', 'Assessment Plan', frm.doc.assessment_plan);
			}, __('View'));
		}
	},
});
