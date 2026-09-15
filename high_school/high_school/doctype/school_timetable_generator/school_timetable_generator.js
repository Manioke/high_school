/* Preview is read-only; Apply uses a server-verified preview token. */
frappe.ui.form.on('School Timetable Generator', {
    setup(frm) {
        frm.set_query('school_term', () => ({ filters: { academic_year: frm.doc.academic_year } }));
        frm.set_query('student_batch', () => ({ filters: { custom_program: frm.doc.program } }));
        frm.set_query('student_group', 'courses', () => ({ filters: { academic_year: frm.doc.academic_year, program: frm.doc.program } }));
    },
    refresh(frm) {
        frappe.db.get_single_value('School MIS Settings', 'require_rooms_for_timetable').then((required) => {
            const grid = frm.fields_dict.courses && frm.fields_dict.courses.grid;
            if (grid) grid.update_docfield_property('room', 'reqd', Number(required || 0) === 1);
        });
        if (frm.is_new()) return;
        frm.add_custom_button(__('Load / Refresh Courses'), () => {
            frappe.confirm(__('Refresh detected courses? Existing teacher and load choices for matching rows are preserved; rows outside the selected groups are removed.'), async () => {
                if (frm.is_dirty()) {
                    if (!frappe.ui.form.check_mandatory(frm)) return;
                    await frm.save();
                }
                await frm.call('load_courses');
                await frm.reload_doc();
            });
        });
        frm.add_custom_button(__('Tomorrow'), () => frm.set_value('effective_from', frappe.datetime.add_days(frappe.datetime.get_today(), 1)), __('Start Date'));
        frm.add_custom_button(__('In Two Days'), () => frm.set_value('effective_from', frappe.datetime.add_days(frappe.datetime.get_today(), 2)), __('Start Date'));
        frm.add_custom_button(__('Next Monday'), () => {
            const today = frappe.datetime.get_today();
            const day = new Date(today + 'T12:00:00').getDay();
            frm.set_value('effective_from', frappe.datetime.add_days(today, ((8 - day) % 7) || 7));
        }, __('Start Date'));
        frm.add_custom_button(__('Preview Schedule Changes'), () => timetable_preview(frm), __('Actions'));
        frm.add_custom_button(__('Open Course Schedules'), () => frappe.set_route('List', 'Course Schedule', { custom_timetable_generator: frm.doc.name }), __('View'));
        frm.add_custom_button(__('Print Weekly Timetable'), () => {
            const d = new frappe.ui.Dialog({ title: __('Print Weekly Timetable'), fields: [
                { fieldname: 'week_start', label: __('Any Date in the Week'), fieldtype: 'Date', reqd: 1, default: frm.doc.effective_from || frappe.datetime.get_today() },
                { fieldname: 'student_group', label: __('Student Group'), fieldtype: 'Link', options: 'Student Group', get_query: () => ({ filters: { academic_year: frm.doc.academic_year, program: frm.doc.program } }) },
                { fieldname: 'instructor', label: __('Instructor'), fieldtype: 'Link', options: 'Instructor' },
                { fieldname: 'help', fieldtype: 'HTML', options: __('Choose one class or one teacher for a readable weekly grid. It includes saved schedules from all generators in the selected scope.') }
            ], primary_action_label: __('Open Printable Grid'), primary_action: async (values) => {
                if (!!values.student_group === !!values.instructor) {
                    frappe.msgprint(__('Choose either a Student Group or an Instructor.'));
                    return;
                }
                // Open during the click gesture to avoid popup blockers.
                const win = window.open('', '_blank');
                if (!win) { frappe.msgprint(__('Allow popups to open the printable timetable.')); return; }
                try {
                    if (frm.is_dirty()) {
                        if (!frappe.ui.form.check_mandatory(frm)) { win.close(); return; }
                        await frm.save();
                    }
                    const response = await frm.call('print_timetable', values);
                    win.document.open(); win.document.write(response.message); win.document.close();
                    win.opener = null;
                    d.hide();
                } catch (e) { win.close(); console.error(e); }
            }});
            d.show();
        }, __('View'));
        frm.add_custom_button(__('Timetable Report'), () => frappe.set_route('query-report', 'School Course Timetable', {
            academic_year: frm.doc.academic_year, school_term: frm.doc.school_term,
            program: frm.doc.program, student_batch: frm.doc.student_batch || undefined,
            week_start: frm.doc.effective_from || frappe.datetime.get_today()
        }), __('View'));
    }
});

async function timetable_preview(frm) {
    if (frm._timetable_generation_running) return;
    frm._timetable_generation_running = true;
    let frozen = false;
    try {
        if (frm.is_dirty()) {
            if (!frappe.ui.form.check_mandatory(frm)) return;
            await frm.save(); // Never save a clean form: Frappe may not resolve that promise.
        }
        frappe.dom.freeze(__('Checking timetable availability and protected records...'));
        frozen = true;
        const response = await frm.call('preview_schedules');
        const result = response.message;
        frappe.dom.unfreeze(); frozen = false;
        timetable_show_preview(frm, result);
    } catch (error) {
        console.error('Timetable preview failed', error);
        frappe.msgprint(__('Preview could not finish. Review the server message. No schedule changes are made by Preview.'));
    } finally {
        if (frozen) frappe.dom.unfreeze();
        frm._timetable_generation_running = false;
    }
}

function timetable_show_preview(frm, result) {
    const esc = (value) => frappe.utils.escape_html(String(value == null ? '' : value));
    const rows = [...result.removals.map(r => ({ ...r, action: __('Remove') })), ...result.additions.map(r => ({ ...r, action: __('Add') }))];
    const fields = ['action', 'schedule_date', 'from_time', 'to_time', 'student_group', 'course', 'instructor', 'room'];
    const table = rows.slice(0, 200).map(r => '<tr>' + fields.map(k => `<td>${esc(r[k])}</td>`).join('') + '</tr>').join('');
    const workloads = (result.workloads || []).map(r => `<tr><td>${esc(r.instructor)}</td><td>${r.total_lessons}</td><td>${r.busiest_day}</td><td>${r.days_over_limit}</td></tr>`).join('');
    const body = `<p><b>${esc(result.mode)}</b> · ${esc(result.start)} — ${esc(result.end)}</p>
        <p>${__('Add')}: <b>${result.additions.length}</b> · ${__('Remove')}: <b>${result.removals.length}</b> · ${__('Unchanged owned records')}: ${result.retained.length} · ${__('Other existing records kept')}: ${result.unaffected}</p>
        <p>${esc(result.warning)}</p><details><summary>${__('Teacher workload after these changes')}</summary><p>${__('Totals cover the selected date range and include other saved classes. Existing lessons outside this replacement may already exceed a new daily limit.')}</p><table class="table"><tr><th>${__('Teacher')}</th><th>${__('Total lessons')}</th><th>${__('Busiest day')}</th><th>${__('Days above daily limit')}</th></tr>${workloads}</table></details><p>${__('Showing the first 200 changes. Download the complete preview to review all changes and weekly lesson targets. Preview expires after 15 minutes.')}</p>
        <div style="max-height:420px;overflow:auto"><table class="table table-bordered"><thead><tr>${[__('Change'), __('Date'), __('From'), __('To'), __('Group'), __('Course'), __('Teacher'), __('Room')].map(s => `<th>${s}</th>`).join('')}</tr></thead><tbody>${table || `<tr><td colspan="8">${__('No changes needed.')}</td></tr>`}</tbody></table></div>`;
    const dialog = new frappe.ui.Dialog({title: __('Review Timetable Changes'), size: 'extra-large', fields: [{fieldname: 'preview', fieldtype: 'HTML', options: body}],
        secondary_action_label: __('Download Full Preview'), secondary_action: () => {
            const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = 'timetable-preview.json'; a.click();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        },
        primary_action_label: __('Apply These Changes'), primary_action: async () => {
            if (dialog._applying) return;
            if (frm.is_dirty()) { frappe.msgprint(__('Save your changes and preview again.')); return; }
            dialog._applying = true;
            dialog.disable_primary_action();
            try {
                frappe.dom.freeze(__('Applying timetable changes. Please keep this page open...'));
                const response = await frm.call('apply_schedules', { token: result.token });
                dialog.hide();
                const applied = response.message;
                frappe.msgprint(__('Created {0}, removed {1}, retained {2} unchanged schedule(s).', [applied.created.length, applied.removed.length, applied.retained]));
                await frm.reload_doc();
            } catch (error) {
                console.error('Timetable apply failed', error);
                frappe.msgprint(__('Apply did not return success. If the connection timed out, check the generator timeline and Course Schedules before trying again; the server may still be working. Otherwise resolve the reported issue and preview again.'));
            } finally {
                frappe.dom.unfreeze();
                dialog._applying = false;
                dialog.enable_primary_action();
            }
        }});
    dialog.show();
    if (!rows.length) dialog.disable_primary_action();
}
