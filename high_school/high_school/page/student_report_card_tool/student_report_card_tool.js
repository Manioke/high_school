frappe.pages['student-report-card-tool'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({ parent: wrapper, title: __('Bulk Performance Summaries & Report Cards'), single_column: true });
    const fields = {};
    const add = (df) => { fields[df.fieldname] = page.add_field(df); return fields[df.fieldname]; };

    add({ fieldname: 'program', label: __('Program'), fieldtype: 'Link', options: 'Program', reqd: 1 });
    add({ fieldname: 'academic_year', label: __('Academic Year'), fieldtype: 'Link', options: 'Academic Year', reqd: 1 });
    add({ fieldname: 'school_term', label: __('School Term'), fieldtype: 'Link', options: 'School Term', reqd: 1,
        get_query: () => ({ filters: { academic_year: fields.academic_year.get_value() } }) });
    add({ fieldname: 'student_batch', label: __('Student Batch'), fieldtype: 'Link', options: 'Student Batch Name', reqd: 1,
        get_query: () => ({ filters: { custom_program: fields.program.get_value() } }) });
    add({ fieldname: 'include_incomplete', label: __('Include Incomplete'), fieldtype: 'Check', default: 0 });
    add({ fieldname: 'include_drafts', label: __('Include Draft Summaries'), fieldtype: 'Check', default: 1 });
    add({ fieldname: 'letter_head', label: __('Letter Head'), fieldtype: 'Link', options: 'Letter Head' });
    add({ fieldname: 'print_format', label: __('Report Card Template'), fieldtype: 'Link', options: 'Print Format', reqd: 1,
        get_query: () => ({ filters: { doc_type: 'Student Performance Summary' } }) });

    const routeOptions = frappe.route_options || {};
    frappe.route_options = null;
    Object.entries(routeOptions).forEach(([name, value]) => fields[name] && fields[name].set_value(value));
    frappe.db.get_single_value('School MIS Settings', 'student_report_card_print_format').then(value => fields.print_format.set_value(value || 'Student Performance Report Card'));
    frappe.db.get_single_value('School MIS Settings', 'student_report_card_letter_head').then(value => { if (value && !fields.letter_head.get_value()) fields.letter_head.set_value(value); });

    const $body = $(`<div style="padding:18px 0;max-width:1100px;">
        <div class="alert alert-info">${__('This tool uses Student Performance Summary and its merit position. Generate or refresh summaries, check the preview, then download one combined PDF for the selected batch.')}</div>
        <div class="report-card-status text-muted">${__('Choose all four scope fields, then find report cards.')}</div>
        <div class="report-card-results" style="margin-top:16px;"></div>
    </div>`).appendTo(page.main);

    page.set_primary_action(__('Find Report Cards'), preview);
    page.add_inner_button(__('Generate / Refresh Summaries'), generate);
    page.add_inner_button(__('Download Combined PDF'), download);

    function values() {
        const args = Object.fromEntries(Object.entries(fields).map(([name, field]) => [name, field.get_value()]));
        for (const name of ['program', 'academic_year', 'school_term', 'student_batch', 'print_format']) {
            if (!args[name]) { frappe.msgprint(__('Please select {0}.', [fields[name].df.label])); return null; }
        }
        return args;
    }

    function preview() {
        const args = values(); if (!args) return;
        frappe.call({ method: 'high_school.high_school.report_cards.get_report_card_preview', args, freeze: true,
            callback: (r) => render(r.message || {}) });
    }

    function render(data) {
        $('.report-card-status').text(data.message || '');
        const rows = (data.rows || []).map(row => `<tr><td>${frappe.utils.escape_html(row.student_group)}</td><td>${frappe.utils.escape_html(row.performance_period)}</td><td>${row.report_cards}</td><td>${row.complete}</td><td>${row.incomplete}</td><td>${row.submitted}</td><td>${row.draft}</td></tr>`).join('');
        $('.report-card-results').html(`<div style="overflow-x:auto"><table class="table table-bordered"><thead><tr><th>${__('Student Group')}</th><th>${__('Performance Period')}</th><th>${__('Reports')}</th><th>${__('Complete')}</th><th>${__('Incomplete')}</th><th>${__('Submitted')}</th><th>${__('Draft')}</th></tr></thead><tbody>${rows || `<tr><td colspan="7">${__('No matching performance periods.')}</td></tr>`}</tbody></table></div>`);
    }

    function generate() {
        const args = values(); if (!args) return;
        frappe.confirm(__('Generate or refresh draft performance summaries for every matching group? Submitted summaries will not be changed.'), () => {
            frappe.call({ method: 'high_school.high_school.report_cards.generate_batch_performance_summaries', args, freeze: true,
                freeze_message: __('Calculating performance summaries'), callback: (r) => {
                    const result = r.message || {}; const failed = (result.results || []).filter(row => !row.ok);
                    frappe.msgprint({ title: __('Generation Complete'), indicator: failed.length ? 'orange' : 'green',
                        message: __('{0} period(s) completed; {1} failed.', [result.success_count || 0, failed.length]) + (failed.length ? '<br>' + failed.map(row => `${frappe.utils.escape_html(row.performance_period)}: ${frappe.utils.escape_html(row.error)}`).join('<br>') : '') });
                    preview();
                } });
        });
    }

    function download() {
        const args = values(); if (!args) return;
        const query = new URLSearchParams(args).toString();
        window.open(`/api/method/high_school.high_school.report_cards.download_report_cards?${query}`, '_blank');
    }
};
