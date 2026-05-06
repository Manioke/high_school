frappe.pages['taliui-ngaue-tool'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Taliui Akonofo Tool',
        single_column: true
    });

    // 1. Setup Filters
    let house_f = page.add_field({
        label: 'School House', 
        fieldtype: 'Link', 
        options: 'School House', 
        fieldname: 'house'
    });

    let shift_f = page.add_field({
        label: 'Taliui', 
        fieldtype: 'Select', 
        options: ['Pongipongi', 'Ngaue', 'Mohe'], 
        fieldname: 'shift', 
        default: 'Pongipongi'
    });

    let date_f = page.add_field({
        label: 'Date', 
        fieldtype: 'Date', 
        default: frappe.datetime.nowdate(), 
        fieldname: 'date'
    });

    // Main area for the tool
    let $container = $('<div class="student-area" style="padding: 15px;"></div>').appendTo(page.main);

    // 2. Validation & Fetching Logic
    const refresh = () => {
        let house = house_f.get_value();
        let date = date_f.get_value();
        let shift = shift_f.get_value();

        if (!house) return;

        // Date Validation: Prevent future dates
        if (date > frappe.datetime.get_today()) {
            $container.html('<div class="alert alert-danger">Cannot mark attendance for future dates.</div>');
            frappe.throw(__('Cannot mark attendance for future dates.'));
            return;
        }

        $container.html('<div class="text-muted">Fetching students...</div>');

        frappe.call({
            method: "high_school.high_school.api.get_taliui_records",
            args: {
                house: house,
                date: date,
                taliui: shift
            },
            callback: (r) => {
                render_student_grid(page, $container, r.message || []);
            }
        });
    };

    // Trigger refresh on filter change
    house_f.$input.on('change', refresh);
    shift_f.$input.on('change', refresh);
    date_f.$input.on('change', refresh);

    // 3. Grid Rendering (The UI)
    function render_student_grid(page, wrapper, students) {
        wrapper.empty();
        if (students.length === 0) {
            wrapper.html('<div class="text-muted">No Students found in this House.</div>');
            return;
        }

        // Toolbar Logic
        let toolbar = $(`<div class="tool-toolbar" style="margin-bottom: 15px;">
            <button class="btn btn-default btn-xs btn-check-all" style="margin-right: 5px;">Check all</button>
            <button class="btn btn-default btn-xs btn-uncheck-all" style="margin-right: 5px;">Uncheck all</button>
            <button class="btn btn-primary btn-xs btn-mark-att">Mark Attendance</button>
        </div>`).appendTo(wrapper);

        toolbar.find('.btn-check-all').click(() => {
            wrapper.find('input[type="checkbox"]:not(:disabled)').prop('checked', true);
        });

        toolbar.find('.btn-uncheck-all').click(() => {
            wrapper.find('input[type="checkbox"]:not(:disabled)').prop('checked', false);
        });

        toolbar.find('.btn-mark-att').click(() => {
            let studs = [];
            wrapper.find('input[type="checkbox"]').each(function() {
                let $chk = $(this);
                studs.push({
                    student: $chk.data('student'),
                    checked: $chk.is(':checked'),
                    disabled: $chk.prop('disabled')
                });
            });

            // Calculate Counts for Confirmation
            let present = studs.filter(s => s.checked && !s.disabled);
            let absent = studs.filter(s => !s.checked && !s.disabled);

            frappe.confirm(
                __('Do you want to update attendance? <br><br> <b>Present:</b> {0} <br> <b>Absent:</b> {1}', [present.length, absent.length]),
                () => {
                    frappe.call({
                        method: "high_school.high_school.api.mark_taliui_attendance",
                        freeze: true,
                        freeze_message: __('Marking attendance'),
                        args: {
                            students_present: present,
                            students_absent: absent,
                            house: house_f.get_value(),
                            taliui: shift_f.get_value(),
                            date: date_f.get_value()
                        },
                        callback: (r) => {
                            if(!r.exc) {
                                frappe.show_alert({message: __('Attendance Updated'), indicator: 'green'});
                                refresh();
                            }
                        }
                    });
                }
            );
        });

        // 4. Vertical List with Scrollbar
        // Adjust 'max-height' as needed for your screen size
        let list_container = $(`
            <div class="student-list-container" style="
                border: 1px solid #d1d8dd; 
                border-radius: 4px; 
                max-height: 500px; 
                overflow-y: auto; 
                background: #fff;
            ">
            </div>
        `).appendTo(wrapper);
        
        students.forEach(s => {
            let is_leave = s.status === "Leave";
            
            list_container.append(`
                <div class="student-row" style="padding: 10px 15px; border-bottom: 1px solid #f0f0f0;">
                    <div class="checkbox" style="margin: 0;">
                        <label style="${is_leave ? 'color: #ff9800; font-weight: bold;' : ''}; display: flex; align-items: center; cursor: pointer; width: 100%;">
                            <input type="checkbox" 
                                class="students-check" 
                                style="margin: 0; width: 18px; height: 18px;"
                                data-student="${s.student}" 
                                ${s.status === "Present" ? "checked" : ""}
                                ${is_leave ? "disabled" : ""}>
                            <span style="margin-left: 12px; font-size: 1.1em;">
                                ${s.student_name} ${is_leave ? '<small>(On Leave)</small>' : ''}
                            </span>
                        </label>
                    </div>
                </div>
            `);
        });
    }
};