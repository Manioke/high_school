frappe.pages['executive-dashboard'].on_page_load = function(wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'School Executive Dashboard',
        single_column: true
    });

    $(page.body).html(`
        <div class="executive-dashboard-container" style="padding: 15px;">

            <!-- Controls -->
            <div class="card" style="
                padding: 15px;
                margin-bottom: 20px;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 15px;
                ">

                    <div style="font-weight: 600;">
                        School Term
                    </div>

                    <select
                        id="school-term-selector"
                        class="form-control"
                        style="max-width: 250px;"
                    >
                        <option value="">
                            Loading terms...
                        </option>
                    </select>

                    <div id="term-dates"
                         style="color: #6c757d;">
                    </div>

                </div>
            </div>


            <!-- KPI Cards -->
            <div
                id="executive-kpis"
                style="
                    display: grid;
                    grid-template-columns:
                        repeat(auto-fit, minmax(220px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                "
            >
                <div class="card" style="padding: 20px;">
                    Loading...
                </div>
            </div>


            <!-- Executive Briefing -->
            <div
                class="card"
                style="
                    padding: 20px;
                    margin-bottom: 20px;
                    background-color: #f8f9fa;
                    border-left: 4px solid #007bff;
                "
            >

                <h4 style="margin-top: 0;">
                    📋 Executive Briefing
                </h4>

                <div id="executive-summary-content">
                    <i>
                        Loading executive summary...
                    </i>
                </div>

            </div>


            <!-- Insights -->
            <div class="card" style="padding: 10px;">

                <h4 style="padding: 10px;">
                    📊 Attendance Analytics
                </h4>

                <iframe
                    id="insights-dashboard"
                    src=""
                    style="
                        width: 100%;
                        height: 750px;
                        border: none;
                    "
                ></iframe>

            </div>

        </div>
    `);


    // ---------------------------------------------------------
    // Load School Terms
    // ---------------------------------------------------------

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'School Term',

            fields: [
                'name',
                'academic_year',
                'term',
                'start_date',
                'end_date'
            ],

            order_by: 'start_date desc',

            limit_page_length: 50
        },

        callback: function(r) {

            const terms = r.message || [];

            const selector =
                $('#school-term-selector');

            selector.empty();

            if (!terms.length) {

                selector.append(`
                    <option value="">
                        No School Terms found
                    </option>
                `);

                return;
            }


            // Determine current term

            const today = frappe.datetime.get_today();

            let currentTerm = null;

            terms.forEach(term => {

                if (
                    term.start_date <= today &&
                    term.end_date >= today
                ) {
                    currentTerm = term;
                }

            });


            // Add options

            terms.forEach(term => {

                const selected =
                    currentTerm &&
                    currentTerm.name === term.name
                        ? 'selected'
                        : '';

                selector.append(`
                    <option
                        value="${term.name}"
                        ${selected}
                    >
                        ${term.academic_year}
                        - ${term.term}
                    </option>
                `);

            });


            // Load selected term

            const selectedTerm =
                currentTerm || terms[0];

            loadExecutiveSummary(
                selectedTerm.name
            );


            updateTermDates(selectedTerm);


            // Change handler

            selector.on('change', function() {

                const termName = $(this).val();

                const term = terms.find(
                    t => t.name === termName
                );

                if (term) {

                    updateTermDates(term);

                    loadExecutiveSummary(
                        term.name
                    );

                }

            });

        }
    });


    // ---------------------------------------------------------
    // Update term dates
    // ---------------------------------------------------------

    function updateTermDates(term) {

        $('#term-dates').html(`
            ${term.start_date}
            →
            ${term.end_date}
        `);

    }


    // ---------------------------------------------------------
    // Load Executive Summary
    // ---------------------------------------------------------

    function loadExecutiveSummary(schoolTerm) {

        $('#executive-summary-content').html(`
            <i>
                Loading executive summary...
            </i>
        `);

        $('#executive-kpis').html(`
            <div class="card" style="padding: 20px;">
                Loading...
            </div>
        `);


        frappe.call({

            method:
                'high_school.high_school.executive_mis.get_executive_summary',

            args: {
                school_term: schoolTerm
            },

            callback: function(r) {

                if (!r.message) {

                    $('#executive-summary-content')
                        .html(`
                            <p>
                                Unable to load executive summary.
                            </p>
                        `);

                    return;
                }


                const data = r.message;


                // ---------------------------------------------
                // Handle errors
                // ---------------------------------------------

                if (data.error) {

                    $('#executive-summary-content')
                        .html(`
                            <p>
                                ${data.error}
                            </p>
                        `);

                    return;
                }


                const attendance =
                    data.attendance;


                // ---------------------------------------------
                // Attendance KPI
                // ---------------------------------------------

                let attendanceDisplay =
                    attendance.attendance_rate !== null
                        ? `${attendance.attendance_rate}%`
                        : 'N/A';


                let statusText =
                    attendance.status === 'healthy'
                        ? 'Healthy'
                        : 'Needs Attention';


                $('#executive-kpis').html(`

                    <div class="card"
                         style="padding: 20px;">

                        <div style="
                            color: #6c757d;
                            font-size: 13px;
                            text-transform: uppercase;
                        ">
                            Attendance
                        </div>

                        <div style="
                            font-size: 32px;
                            font-weight: 700;
                            margin-top: 8px;
                        ">
                            ${attendanceDisplay}
                        </div>

                        <div style="
                            margin-top: 5px;
                            color: #6c757d;
                        ">
                            Target:
                            ${attendance.target}%
                        </div>

                    </div>


                    <div class="card"
                         style="padding: 20px;">

                        <div style="
                            color: #6c757d;
                            font-size: 13px;
                            text-transform: uppercase;
                        ">
                            Absent
                        </div>

                        <div style="
                            font-size: 32px;
                            font-weight: 700;
                            margin-top: 8px;
                        ">
                            ${attendance.absent}
                        </div>

                    </div>


                    <div class="card"
                         style="padding: 20px;">

                        <div style="
                            color: #6c757d;
                            font-size: 13px;
                            text-transform: uppercase;
                        ">
                            Leave
                        </div>

                        <div style="
                            font-size: 32px;
                            font-weight: 700;
                            margin-top: 8px;
                        ">
                            ${attendance.leave}
                        </div>

                    </div>


                    <div class="card"
                         style="padding: 20px;">

                        <div style="
                            color: #6c757d;
                            font-size: 13px;
                            text-transform: uppercase;
                        ">
                            Groups Below Target
                        </div>

                        <div style="
                            font-size: 32px;
                            font-weight: 700;
                            margin-top: 8px;
                        ">
                            ${attendance.groups_below_target}
                        </div>

                    </div>

                `);


                // ---------------------------------------------
                // Executive summary
                // ---------------------------------------------

                $('#executive-summary-content')
                    .html(data.summary_html);


                // ---------------------------------------------
                // Insights dashboard
                // ---------------------------------------------

                /*
                 * Put your actual Insights dashboard URL here.
                 *
                 * Example:
                 *
                 * $('#insights-dashboard').attr(
                 *     'src',
                 *     '/insights/dashboards/...'
                 * );
                 */

            }

        });

    }

};