frappe.ui.form.on('School Examination Cycle', {
	setup(frm) {
		frm.set_query('hod_user', 'hod_assignments', () => ({
			filters: { enabled: 1, user_type: 'System User' },
		}));
		frm.set_query('student_batch', 'courses', () => {
			const batches = (frm.doc.student_batches || [])
				.map((row) => row.student_batch)
				.filter(Boolean);
			return batches.length ? { filters: { name: ['in', batches] } } : {};
		});
	},

	refresh(frm) {
		render_form_course_buttons(frm);
		if (!frm.is_new() && frm.doc.status !== 'Closed') {
			frm.add_custom_button(__('Generate / Refresh Paper Requirements'), () => {
				frappe.confirm(
					__('Generate missing requirements and refresh their affected Student Groups? Existing teacher submissions will be preserved.'),
					() => frm.call('generate_requirements').then((r) => {
						const result = r.message || {};
						let message = __('Created {0}, refreshed {1}, found {2} without Student Group mapping, and found {3} without an automatic HOD mapping.', [
							result.created || 0,
							result.updated || 0,
							result.without_groups || 0,
							result.without_hod || 0,
						]);
						if (result.out_of_scope) {
							message += '<br><br>' + __('{0} existing requirement(s) are no longer in the selected Batch–Course scope and were preserved for safety. Review and delete the incorrect ones manually: {1}', [
								result.out_of_scope,
								frappe.utils.escape_html((result.out_of_scope_requirements || []).join(', ')),
							]);
						}
						if (result.without_hod && (result.hod_mapping_issues || []).length) {
							message += '<br><br><b>' + __('HOD mapping issues:') + '</b><br>'
								+ (result.hod_mapping_issues || [])
									.map((issue) => frappe.utils.escape_html(issue))
									.join('<br>');
						}
						frappe.msgprint(message);
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

	course_selection_policy(frm) {
		render_form_course_buttons(frm);
	},
});

function render_form_course_buttons(frm) {
	const field = frm.fields_dict.courses;
	if (!field) return;
	const $wrapper = field.$wrapper || $(field.wrapper);
	$wrapper.find('.school-form-course-loaders').remove();
	if (frm.doc.course_selection_policy !== 'Selected Courses') return;

	const $actions = $('<div class="school-form-course-loaders" style="display:flex; gap:8px; flex-wrap:wrap; margin-top:10px;"></div>');
	[5, 6, 7].forEach((formLevel) => {
		$('<button type="button" class="btn btn-default btn-xs"></button>')
			.text(__(`Get Form ${formLevel} Courses`))
			.on('click', () => load_form_courses(frm, formLevel))
			.appendTo($actions);
	});
	$wrapper.append($actions);
}

function load_form_courses(frm, formLevel) {
	if (!frm.doc.academic_year) {
		frappe.msgprint(__('Select an Academic Year first.'));
		return;
	}
	frappe.call({
		method: 'high_school.high_school.exam_preparation.get_form_course_rows',
		args: {
			academic_year: frm.doc.academic_year,
			student_batches: frm.doc.student_batches || [],
			form_level: formLevel,
		},
		freeze: true,
		freeze_message: __(`Loading Form ${formLevel} Courses...`),
		callback(r) {
			const response = r.message || {};
			const existing = new Set(
				(frm.doc.courses || []).map((row) => `${row.student_batch || ''}::${row.course || ''}`)
			);
			let added = 0;
			(response.rows || []).forEach((row) => {
				const key = `${row.student_batch || ''}::${row.course || ''}`;
				if (existing.has(key)) return;
				frm.add_child('courses', row);
				existing.add(key);
				added += 1;
			});
			frm.refresh_field('courses');
			render_form_course_buttons(frm);
			frappe.show_alert({
				message: __('Added {0} Form {1} course(s) for {2}.', [
					added,
					formLevel,
					response.student_batch || '',
				]),
				indicator: added ? 'green' : 'blue',
			});
		},
	});
}
