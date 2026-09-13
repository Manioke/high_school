frappe.pages['bulk-assessment-plan-tool'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: __('Bulk Assessment Plan Tool'), single_column: true });
    const fields = {};
    const add = (df) => { fields[df.fieldname] = page.add_field(df); return fields[df.fieldname]; };
    add({ fieldname: 'academic_year', label: __('Academic Year'), fieldtype: 'Link', options: 'Academic Year', reqd: 1 });
    add({ fieldname: 'program', label: __('Program'), fieldtype: 'Link', options: 'Program', reqd: 1 });
    add({ fieldname: 'school_term', label: __('School Term'), fieldtype: 'Link', options: 'School Term', reqd: 1, get_query: () => ({ filters: { academic_year: fields.academic_year.get_value() } }) });
    add({ fieldname: 'assessment_group', label: __('Assessment Group'), fieldtype: 'Link', options: 'Assessment Group' });
    add({ fieldname: 'student_batch', label: __('Student Batch'), fieldtype: 'Link', options: 'Student Batch Name',
        get_query: () => ({ filters: { custom_program: fields.program.get_value() } }) });
    const routeOptions = frappe.route_options || {};
    frappe.route_options = null;
    Object.entries(routeOptions).forEach(([name, value]) => fields[name] && fields[name].set_value(value));

    const $body = $(`<div style="padding:18px 0;max-width:1200px">
        <div class="alert alert-info">${__('Select approved Exam Paper Requirements. Their approved criteria, affected Student Groups, grading scale, exam date and School Period times remain authoritative; existing Assessment Plans are skipped.')}</div>
        <div class="bulk-plan-status text-muted">${__('Choose an Academic Year and School Term.')}</div>
        <div class="bulk-plan-results" style="margin-top:16px"></div>
    </div>`).appendTo(page.main);
    let rows = [];

    page.set_primary_action(__('Find Approved Papers'), load);
    page.add_inner_button(__('Create Selected Assessment Plans'), createSelected);

    function args() {
        const values = Object.fromEntries(Object.entries(fields).map(([name, field]) => [name, field.get_value()]));
        if (!values.academic_year || !values.program || !values.school_term) {
            frappe.msgprint(__('Academic Year, Program, and School Term are required.'));
            return null;
        }
        return values;
    }
    function load() {
        const values = args(); if (!values) return;
        frappe.call({ method: 'high_school.high_school.assessment_plan_setup.get_bulk_approved_requirements', args: values, freeze: true, callback(r) {
            rows = r.message || [];
            $('.bulk-plan-status').text(__('{0} approved paper requirement(s) found.', [rows.length]));
            const body = rows.map((row, index) => `<tr>
                <td><input type="checkbox" class="bulk-plan-select" data-index="${index}" ${Number(row.missing_plan_count || 0) > 0 ? 'checked' : 'disabled'}></td>
                <td><a href="/app/exam-paper-requirement/${encodeURIComponent(row.name)}">${frappe.utils.escape_html(row.name)}</a></td>
                <td>${frappe.utils.escape_html(row.student_batch || '')}</td><td>${frappe.utils.escape_html(row.course || '')}</td>
                <td>${frappe.utils.escape_html(row.assessment_group || '')}</td><td>${frappe.datetime.str_to_user(row.examination_date || '')}</td>
                <td>${row.created_plan_count || 0} / ${row.expected_plan_count || 0}</td><td>${frappe.utils.escape_html(row.status || '')}</td>
            </tr>`).join('');
            $('.bulk-plan-results').html(`<div style="overflow-x:auto"><table class="table table-bordered table-hover"><thead><tr><th></th><th>${__('Requirement')}</th><th>${__('Batch')}</th><th>${__('Course')}</th><th>${__('Assessment Group')}</th><th>${__('Exam Date')}</th><th>${__('Plans')}</th><th>${__('Status')}</th></tr></thead><tbody>${body || `<tr><td colspan="8">${__('No approved papers match these filters.')}</td></tr>`}</tbody></table></div>`);
        }});
    }
    function createSelected() {
        const selected = $('.bulk-plan-select:checked').map((_, el) => rows[Number($(el).data('index'))].name).get();
        if (!selected.length) return frappe.msgprint(__('Select at least one paper with missing Assessment Plans.'));
        frappe.confirm(__('Create all missing Assessment Plans for {0} selected paper(s)?', [selected.length]), () => {
            frappe.call({ method: 'high_school.high_school.assessment_plan_setup.create_bulk_approved_assessment_plans', args: { requirements: JSON.stringify(selected) }, freeze: true, freeze_message: __('Creating Assessment Plans...'), callback(r) {
                const result = r.message || {}; const failed = (result.results || []).filter(row => !row.ok);
                frappe.msgprint({ title: __('Bulk Assessment Plan Result'), indicator: failed.length ? 'orange' : 'green', message: __('Created {0}, submitted {1}, failed {2}.', [result.created || 0, result.submitted || 0, result.failed || 0]) + (failed.length ? '<br><br>' + failed.map(row => `${frappe.utils.escape_html(row.requirement)}: ${frappe.utils.escape_html(row.error)}`).join('<br>') : '') });
                load();
            }});
        });
    }
};
