frappe.ui.form.on("School Performance Period", {
	setup(frm) {
		frm.set_query("school_term", () => ({
			filters: { academic_year: frm.doc.academic_year },
		}));
		frm.set_query("main_student_group", () => ({
			filters: { academic_year: frm.doc.academic_year },
		}));
	},

	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("View Performance Summaries"), () => {
			frappe.set_route("List", "Student Performance Summary", {
				performance_period: frm.doc.name,
			});
		}, __("Results"));

		frm.add_custom_button(__("Generate Performance Summaries"), () => {
			frappe.call({
				method: "high_school.high_school.performance.generate_performance_summaries",
				args: { performance_period: frm.doc.name },
				freeze: true,
				freeze_message: __("Calculating results and rankings..."),
				callback(r) {
					if (!r.message) return;
					frappe.msgprint(
						__("Processed {0} students. Updated {1}; skipped {2} submitted summaries.", [
							r.message.total_students,
							r.message.created_or_updated,
							r.message.skipped_submitted,
						])
					);
				},
			});
		}, __("Results"));
	},
});
