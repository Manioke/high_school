frappe.pages['taliui-ngaue-tool'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Taliui Akonofo Tool',
        single_column: true
    });

    // Filters
    let house_f = page.add_field({label: 'School House', fieldtype: 'Link', options: 'School House', fieldname: 'house'});
    let shift_f = page.add_field({label: 'Taliui', fieldtype: 'Select', options: ['Pongipongi', 'Ngaue', 'Mohe'], fieldname: 'shift', default: 'Pongipongi'});
    let date_f = page.add_field({label: 'Date', fieldtype: 'Date', default: frappe.datetime.nowdate(), fieldname: 'date'});

    let $container = $('<div class="student-area" style="padding: 15px;"></div>').appendTo(page.main);

    const refresh = () => {
        if (!house_f.get_value()) return;
        $container.html('<div class="text-muted">Fetching...</div>');

        frappe.call({
            method: "high_school.high_school.api.get_taliui_records",
            args: {
                house: house_f.get_value(),
                date: date_f.get_value(),
                taliui: shift_f.get_value()
            },
            callback: (r) => {
                render_student_grid(page, $container, r.message || []);
            }
        });
    };

    house_f.$input.on('change', refresh);
    shift_f.$input.on('change', refresh);
    date_f.$input.on('change', refresh);

    function render_student_grid(page, wrapper, students) {
        wrapper.empty();
        if (students.length === 0) {
            wrapper.html('<div class="text-muted">No Students found in this House.</div>');
            return;
        }

        // Toolbar
        let toolbar = $(`<p>
            <button class="btn btn-default btn-xs btn-check-all">Check all</button>
            <button class="btn btn-default btn-xs btn-uncheck-all">Uncheck all</button>
            <button class="btn btn-primary btn-xs btn-mark">Mark Attendance</button>
        </p>`).appendTo(wrapper);

        toolbar.find('.btn-check-all').click(() => wrapper.find('input[type="checkbox"]:not(:disabled)').prop('checked', true));
        toolbar.find('.btn-uncheck-all').click(() => wrapper.find('input[type="checkbox"]:not(:disabled)').prop('checked', false));
        
        toolbar.find('.btn-mark').click(() => {
            let studs = [];
            wrapper.find('input[type="checkbox"]').each(function() {
                let $chk = $(this);
                studs.push({
                    student: $chk.data('student'),
                    checked: $chk.is(':checked'),
                    disabled: $chk.prop('disabled')
                });
            });

            let present = studs.filter(s => s.checked && !s.disabled);
            let absent = studs.filter(s => !s.checked && !s.disabled);

            frappe.confirm(`Update Attendance?<br>Present: ${present.length}<br>Absent: ${absent.length}`, () => {
                frappe.call({
                    method: "high_school.high_school.api.mark_taliui_attendance",
                    freeze: true,
                    args: {
                        students_present: present,
                        students_absent: absent,
                        house: house_f.get_value(),
                        taliui: shift_f.get_value(),
                        date: date_f.get_value()
                    },
                    callback: refresh
                });
            });
        });

        // Grid
        let grid = $('<div class="row"></div>').appendTo(wrapper);
        students.forEach(s => {
            let is_leave = s.status === "Leave";
            grid.append(`
                <div class="col-sm-3">
                    <div class="checkbox">
                        <label style="${is_leave ? 'color: orange; font-weight: bold;' : ''}">
                            <input type="checkbox" 
                                class="students-check" 
                                data-student="${s.student}" 
                                ${s.status === "Present" ? "checked" : ""}
                                ${is_leave ? "disabled" : ""}>
                            ${s.student_name} ${is_leave ? '(Leave)' : ''}
                        </label>
                    </div>
                </div>
            `);
        });
    }
};