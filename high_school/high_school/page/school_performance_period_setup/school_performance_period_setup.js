frappe.pages['school-performance-period-setup'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('School Performance Period Setup'),
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
		`<div class="school-performance-period-setup" style="padding: 18px 0; max-width: 980px;">
			<div class="alert alert-info">
				${__('Create one School Performance Period for every selected main/home Student Group. Leave Program and Student Batch empty to load the whole school.')}
			</div>
			<div class="text-muted setup-status">
				${__('Choose an Academic Year and School Term, then load the main groups.')}
			</div>
		</div>`
	).appendTo(page.main);

	page.set_primary_action(__('Load Main Groups'), load_groups);

	function get_filters() {
		const values = Object.fromEntries(
			Object.entries(fields).map(([fieldname, control]) => [fieldname, control.get_value()])
		);
		for (const fieldname of ['academic_year', 'school_term']) {
			if (!values[fieldname]) {
				frappe.msgprint(__('Please select {0}.', [fields[fieldname].df.label]));
				return null;
			}
		}
		return values;
	}

	function load_groups() {
		const filters = get_filters();
		if (!filters) return;
		frappe.call({
			method: 'high_school.high_school.performance_period_setup.get_main_group_candidates',
			args: filters,
			freeze: true,
			freeze_message: __('Loading main Student Groups'),
			callback: (r) => open_dialog(filters, r.message || {}),
		});
	}

	function open_dialog(filters, response) {
		const dialog = new frappe.ui.Dialog({
			title: __('Create School Performance Periods'),
			size: 'extra-large',
			fields: [
				{
					fieldname: 'instructions',
					fieldtype: 'HTML',
					options: `<p class="text-muted">${frappe.utils.escape_html(response.message || '')}</p>`,
				},
				{ fieldname: 'rules_section', fieldtype: 'Section Break', label: __('Calculation Rules') },
				{
					fieldname: 'result_status_filter',
					fieldtype: 'Select',
					label: __('Assessment Results to Include'),
					options: 'Draft and Submitted\nSubmitted Only',
					default: 'Draft and Submitted',
					reqd: 1,
				},
				{
					fieldname: 'missing_result_policy',
					fieldtype: 'Select',
					label: __('Missing Result Policy'),
					options: 'Incomplete and Do Not Rank\nCount Missing as Zero\nIgnore Missing Components',
					default: 'Incomplete and Do Not Rank',
					reqd: 1,
				},
				{ fieldname: 'rules_column', fieldtype: 'Column Break' },
				{
					fieldname: 'tie_method',
					fieldtype: 'Select',
					label: __('Tie Ranking Method'),
					options: 'Competition (1, 2, 2, 4)\nDense (1, 2, 2, 3)',
					default: 'Competition (1, 2, 2, 4)',
					reqd: 1,
				},
				{
					fieldname: 'minimum_subjects',
					fieldtype: 'Int',
					label: __('Minimum Subjects Required'),
					default: 1,
					reqd: 1,
				},
				{
					fieldname: 'rounding_precision',
					fieldtype: 'Int',
					label: __('Displayed Decimal Places'),
					default: 2,
					reqd: 1,
				},
				{ fieldname: 'components_section', fieldtype: 'Section Break', label: __('Assessment Components') },
				{
					fieldname: 'components',
					fieldtype: 'Table',
					label: __('Components'),
					reqd: 1,
					in_place_edit: true,
					fields: [
						{ fieldname: 'assessment_group', fieldtype: 'Link', label: __('Assessment Group'), options: 'Assessment Group', in_list_view: 1, reqd: 1 },
						{ fieldname: 'weight', fieldtype: 'Percent', label: __('Weight'), in_list_view: 1, reqd: 1 },
					],
				},
				{ fieldname: 'groups_section', fieldtype: 'Section Break', label: __('Main Student Groups') },
				{
					fieldname: 'groups',
					fieldtype: 'Table',
					label: __('Groups'),
					cannot_add_rows: true,
					in_place_edit: true,
					fields: [
						{ fieldname: 'create_period', fieldtype: 'Check', label: __('Create'), in_list_view: 1 },
						{ fieldname: 'student_group', fieldtype: 'Link', label: __('Main Student Group'), options: 'Student Group', in_list_view: 1, read_only: 1 },
						{ fieldname: 'student_batch', fieldtype: 'Link', label: __('Student Batch'), options: 'Student Batch Name', in_list_view: 1, read_only: 1 },
						{ fieldname: 'student_count', fieldtype: 'Int', label: __('Students'), in_list_view: 1, read_only: 1 },
						{ fieldname: 'existing_period', fieldtype: 'Link', label: __('Existing Period'), options: 'School Performance Period', in_list_view: 1, read_only: 1 },
					],
				},
			],
			primary_action_label: __('Create Performance Periods'),
			primary_action(values) {
				const selected = (values.groups || []).filter((row) => Number(row.create_period || 0));
				if (!selected.length) {
					frappe.msgprint(__('Select at least one main Student Group.'));
					return;
				}
				const settings = {
					...filters,
					result_status_filter: values.result_status_filter,
					missing_result_policy: values.missing_result_policy,
					tie_method: values.tie_method,
					minimum_subjects: values.minimum_subjects,
					rounding_precision: values.rounding_precision,
				};
				frappe.confirm(
					__('Create {0} School Performance Period(s)?', [selected.length]),
					() => frappe.call({
						method: 'high_school.high_school.performance_period_setup.create_performance_periods',
						args: { settings, rows: values.groups, components: values.components },
						freeze: true,
						freeze_message: __('Creating School Performance Periods'),
						callback: (r) => {
							if (r.exc) return;
							const result = r.message || {};
							dialog.hide();
							frappe.msgprint({
								title: __('Performance Period Setup Complete'),
								indicator: 'green',
								message: __('Created {0} period(s). Skipped {1} existing period(s).', [
									(result.created || []).length,
									(result.skipped || []).length,
								]),
							});
							$('.setup-status', $body).text(
								__('Last run created {0} School Performance Period(s).', [(result.created || []).length])
							);
						},
					}),
				);
			},
		});

		dialog.show();
		load_table(dialog, 'components', [{ assessment_group: '', weight: 100 }]);
		load_table(dialog, 'groups', response.rows || []);
	}

	function load_table(dialog, fieldname, rows) {
		const table = dialog.fields_dict[fieldname];
		table.df.data = rows.map((row) => ({ ...row }));
		table.grid.refresh();
	}
};
