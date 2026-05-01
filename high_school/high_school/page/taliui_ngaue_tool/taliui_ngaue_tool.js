frappe.pages['taliui-ngaue-tool'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Taliui Akonofo Tool',
        single_column: true
    });

    // Add Filters
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
        fieldname: 'shift'
    });

    // Create a plain div for the list - No microtemplate needed
    let $container = $('<div class="attendance-area" style="padding: 20px;">' +
                       '<div class="text-muted">Please select a School House to begin.</div>' +
                       '</div>').appendTo(page.main);

    // Function to fetch and render
    const refresh_list = () => {
        let house = house_f.get_value();
        if(!house) return;

        $container.html('<div class="text-muted">Loading Students...</div>');

        frappe.call({
            method: "high_school.api.get_students_by_house",
            args: { house: house },
            callback: function(r) {
                if(r.message) {
                    render_table(page, $container, r.message);
                }
            }
        });
    };

    house_f.$input.on('change', refresh_list);

    // Primary Action Button
    page.set_primary_action('Submit Attendance', () => {
        let rows = [];
        $container.find('.s-row').each(function() {
            rows.push({
                student: $(this).data('name'),
                status: $(this).find('.status-val').val()
            });
        });

        if(rows.length === 0) {
            frappe.msgprint("No students found to submit.");
            return;
        }

        frappe.call({
            method: "high_school.high_school.api.submit_taliui_bulk",
            args: {
                house: house_f.get_value(),
                shift: shift_f.get_value(),
                date: frappe.datetime.nowdate(),
                attendance_json: JSON.stringify(rows)
            },
            callback: function(r) {
                if(!r.exc) {
                    frappe.show_alert({message: __('Attendance Saved Successfully'), indicator: 'green'});
                    refresh_list();
                }
            }
        });
    });
};

function render_table(page, $container, students) {
    let html = `
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th style="width: 60%">Student Name</th>
                    <th style="width: 40%">Status</th>
                </tr>
            </thead>
            <tbody>
    `;

    students.forEach(s => {
        let label = s.on_leave ? ' <span class="label label-warning">On Leave</span>' : '';
        let selected_status = s.on_leave ? 'Leave' : 'Present';
        
        html += `
            <tr class="s-row" data-name="${s.name}">
                <td>${s.student_name}${label}</td>
                <td>
                    <select class="form-control status-val">
                        <option value="Present" ${selected_status === 'Present' ? 'selected' : ''}>Present</option>
                        <option value="Absent">Absent</option>
                        <option value="Leave" ${selected_status === 'Leave' ? 'selected' : ''}>Leave</option>
                    </select>
                </td>
            </tr>
        `;
    });

    html += `</tbody></table>`;
    $container.html(html);
}