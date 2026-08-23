frappe.ui.form.on("Student Performance Summary", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Open Performance Period"), () => {
				frappe.set_route("Form", "School Performance Period", frm.doc.performance_period);
			});
		}
	},
});
