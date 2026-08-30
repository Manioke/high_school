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

		frm.add_custom_button(__("Check Result Readiness"), () => {
			frappe.call({
				method: "high_school.high_school.result_submission.check_performance_readiness",
				args: { performance_period: frm.doc.name },
				freeze: true,
				freeze_message: __("Checking Assessment Plans and submitted results..."),
				callback(r) {
					const result = r.message || {};
					if (result.ready) {
						frappe.msgprint({
							title: __("Results Ready"),
							indicator: "green",
							message: __("Checked {0} plans for {1} students. All required results are submitted or recorded as Did Not Sit/Exempt.", [
								result.plans_checked || 0,
								result.students_checked || 0,
							]),
						});
						return;
					}
					const issues = (result.issues || []).slice(0, 20)
						.map((row) => `<li>${frappe.utils.escape_html(row.message || row.type)}</li>`)
						.join("");
					frappe.msgprint({
						title: __("Assessment Results Not Ready"),
						indicator: "orange",
						message: `<p>${__("Found {0} unresolved issue(s).", [result.issue_count || 0])}</p><ul>${issues}</ul>`,
					});
				},
			});
		}, __("Results"));
	},
});
