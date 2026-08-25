frappe.pages['school-assessment-plan-setup'].on_page_load = function (wrapper) {
	const initial_options = frappe.route_options || {};
	frappe.route_options = null;
	let source_requirement = initial_options.exam_paper_requirement || null;
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('School Assessment Plan Setup'),
		single_column: true,
	});

	const fields = {};
	const add_field = (definition) => {
		fields[definition.fieldname] = page.add_field(definition);
		return fields[definition.fieldname];
	};

	add_field({
		fieldname: 'academic_year',
		label: __('Academic Year'),
		fieldtype: 'Link',
		options: 'Academic Year',
		reqd: 1,
	});
	add_field({
		fieldname: 'school_term',
		label: __('School Term'),
		fieldtype: 'Link',
		options: 'School Term',
		reqd: 1,
		get_query: () => ({ filters: { academic_year: fields.academic_year.get_value() } }),
	});
	add_field({
		fieldname: 'assessment_group',
		label: __('Assessment Group'),
		fieldtype: 'Link',
		options: 'Assessment Group',
		reqd: 1,
	});
	add_field({
		fieldname: 'course',
		label: __('Course / Exam Paper'),
		fieldtype: 'Link',
		options: 'Course',
		reqd: 1,
	});
	add_field({
		fieldname: 'program',
		label: __('Program'),
		fieldtype: 'Link',
		options: 'Program',
	});
	add_field({
		fieldname: 'student_batch',
		label: __('Student Batch'),
		fieldtype: 'Link',
		options: 'Student Batch Name',
	});

	const $body = $(
		`<div class="school-assessment-plan-setup" style="padding: 18px 0; max-width: 980px;">
			<div class="alert alert-info">
				${__('This tool creates standard Education Assessment Plans in bulk. Each plan still belongs to one Student Group and one Course, so the standard Assessment Result Tool continues to work normally.')}
			</div>
			<div class="text-muted setup-status">
				${__('Choose the examination and optional Form filters, then load the teaching groups.')}
			</div>
		</div>`
	).appendTo(page.main);

	page.set_primary_action(__('Load Plans'), () => load_candidates());

	frappe.run_serially(
		Object.entries(initial_options)
			.filter(([fieldname, value]) => fields[fieldname] && value)
			.map(([fieldname, value]) => () => fields[fieldname].set_value(value))
	).then(() => {
		if (source_requirement) load_candidates();
	});

	function required_filters() {
		const values = Object.fromEntries(
			Object.entries(fields).map(([key, control]) => [key, control.get_value()])
		);
		values.exam_paper_requirement = source_requirement;
		for (const fieldname of ['academic_year', 'school_term', 'assessment_group', 'course']) {
			if (!values[fieldname]) {
				frappe.msgprint(__('Please select {0}.', [fields[fieldname].df.label]));
				return null;
			}
		}
		return values;
	}

	function load_candidates() {
		const filters = required_filters();
		if (!filters) return;

		frappe.call({
			method: 'high_school.high_school.assessment_plan_setup.get_setup_candidates',
			args: filters,
			freeze: true,
			freeze_message: __('Loading teaching groups'),
			callback: (r) => open_setup_dialog(filters, r.message || {}),
		});
	}

	function open_setup_dialog(filters, response) {
		const from_approved_paper = Boolean(filters.exam_paper_requirement);
		const dialog = new frappe.ui.Dialog({
			title: __('Create Missing Assessment Plans'),
			size: 'extra-large',
			fields: [
				{
					fieldname: 'instructions',
					fieldtype: 'HTML',
					options: `<p class="text-muted">${frappe.utils.escape_html(response.message || '')}</p>`,
				},
				{ fieldname: 'schedule_section', fieldtype: 'Section Break', label: __('Exam Schedule') },
				{ fieldname: 'schedule_date', fieldtype: 'Date', label: __('Exam Date'), reqd: 1 },
				{ fieldname: 'from_time', fieldtype: 'Time', label: __('Start Time') },
				{ fieldname: 'time_column', fieldtype: 'Column Break' },
				{ fieldname: 'to_time', fieldtype: 'Time', label: __('End Time') },
				{ fieldname: 'room', fieldtype: 'Link', label: __('Default Room'), options: 'Room' },
				{ fieldname: 'grading_scale', fieldtype: 'Link', label: __('Grading Scale'), options: 'Grading Scale' },
				{ fieldname: 'criteria_section', fieldtype: 'Section Break', label: __('Assessment Criteria Used by Every Selected Plan') },
				{
					fieldname: 'criteria',
					fieldtype: 'Table',
					label: __('Assessment Criteria'),
					reqd: 1,
					cannot_add_rows: from_approved_paper,
					read_only: from_approved_paper,
					in_place_edit: true,
					fields: [
						{ fieldname: 'assessment_criteria', fieldtype: 'Link', label: __('Assessment Criterion'), options: 'Assessment Criteria', in_list_view: 1, reqd: 1 },
						{ fieldname: 'maximum_score', fieldtype: 'Float', label: __('Maximum Score'), in_list_view: 1, reqd: 1 },
					],
				},
				{ fieldname: 'plans_section', fieldtype: 'Section Break', label: __('Student Group and Course Plans') },
				{
					fieldname: 'plans',
					fieldtype: 'Table',
					label: __('Plans'),
					cannot_add_rows: from_approved_paper,
					in_place_edit: true,
					fields: [
						{ fieldname: 'create_plan', fieldtype: 'Check', label: __('Create'), default: 1, in_list_view: 1 },
						{ fieldname: 'student_group', fieldtype: 'Link', label: __('Student Group'), options: 'Student Group', in_list_view: 1, read_only: from_approved_paper, reqd: 1 },
						{ fieldname: 'course', fieldtype: 'Link', label: __('Course'), options: 'Course', default: filters.course, in_list_view: 1, read_only: 1, reqd: 1 },
						{ fieldname: 'instructor', fieldtype: 'Link', label: __('Course Instructor'), description: __('Not the exam supervisor.'), options: 'Instructor', in_list_view: 1 },
						{ fieldname: 'room', fieldtype: 'Link', label: __('Room'), options: 'Room', in_list_view: 1 },
						{ fieldname: 'existing_plan', fieldtype: 'Link', label: __('Existing Plan'), options: 'Assessment Plan', in_list_view: 1, read_only: 1 },
					],
				},
			],
			primary_action_label: __('Create Missing Plans'),
			primary_action(values) {
				const selected = (values.plans || []).filter((row) => Number(row.create_plan || 0));
				if (!selected.length) {
					frappe.msgprint(__('Select at least one missing plan.'));
					return;
				}
				const setup = {
					...filters,
					schedule_date: values.schedule_date,
					from_time: values.from_time,
					to_time: values.to_time,
					room: values.room,
					grading_scale: values.grading_scale,
				};
				frappe.confirm(
					__('Create {0} standard Assessment Plan(s)?', [selected.length]),
					() => frappe.call({
						method: 'high_school.high_school.assessment_plan_setup.create_assessment_plans',
						args: { setup, rows: values.plans, criteria: values.criteria },
						freeze: true,
						freeze_message: __('Creating Assessment Plans'),
						callback: (r) => {
							if (r.exc) return;
							const result = r.message || {};
							dialog.hide();
							frappe.msgprint({
								title: __('Assessment Plan Setup Complete'),
								indicator: 'green',
								message: __('Created {0} plan(s). Skipped {1} plan(s) that already existed.', [
									(result.created || []).length,
									(result.skipped || []).length,
								]),
							});
							$('.setup-status', $body).text(
								__('Last run created {0} Assessment Plan(s).', [(result.created || []).length])
							);
						},
					}),
				);
			},
		});

		dialog.show();
		load_dialog_table(dialog, 'criteria', response.criteria || []);
		load_dialog_table(dialog, 'plans', response.rows || []);
		Object.entries(response.schedule_defaults || {}).forEach(([fieldname, value]) => {
			if (value) dialog.set_value(fieldname, value);
		});
	}

	function load_dialog_table(dialog, fieldname, rows) {
		const table = dialog.fields_dict[fieldname];
		table.df.data = rows.map((row) => ({ ...row }));
		table.grid.refresh();
	}
};
