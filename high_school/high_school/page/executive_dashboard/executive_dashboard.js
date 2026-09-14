frappe.pages['executive-dashboard'].on_page_load = function(wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'School Executive Dashboard',
        single_column: true
    });


    // =========================================================
    // Page Layout
    // =========================================================

    $(page.body).html(`

        <div
            class="executive-dashboard-container"
            style="padding: 15px;"
        >

            <!-- ============================================= -->
            <!-- School Term -->
            <!-- ============================================= -->

            <div
                class="card"
                style="
                    padding: 15px;
                    margin-bottom: 20px;
                "
            >

                <div
                    style="
                        display: flex;
                        align-items: center;
                        gap: 15px;
                        flex-wrap: wrap;
                    "
                >

                    <div style="font-weight: 600;">
                        Academic Year
                    </div>

                    <select
                        id="academic-year-selector"
                        class="form-control"
                        style="max-width: 220px;"
                    >
                        <option value="">Loading years...</option>
                    </select>

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

                    <div
                        id="term-dates"
                        style="color: #6c757d;"
                    >
                    </div>

                </div>

            </div>


            <div
                id="school-direction-container"
                class="card"
                style="padding: 20px; margin-bottom: 20px;"
            >
                <div style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; align-items:center;">
                    <h4 style="margin: 0;">School Direction</h4>
                    <div>
                        <button id="create-board-report-btn" class="btn btn-primary btn-sm">Create Board Report</button>
                    </div>
                </div>
                <div id="school-direction-content" class="text-muted">
                    Comparing this term with the previous School Term...
                </div>
            </div>


            <div
                class="card"
                style="padding: 10px; margin-bottom: 20px;"
            >
                <div
                    id="dashboard-section-tabs"
                    style="display: flex; gap: 8px; flex-wrap: wrap;"
                >
                    <button class="btn btn-primary dashboard-section-tab" data-section="attendance">
                        Attendance & Students
                    </button>
                    <button class="btn btn-default dashboard-section-tab" data-section="assessment">
                        Exams & Assessments
                    </button>
                    <button class="btn btn-default dashboard-section-tab" data-section="finance">
                        Fees & Finance
                    </button>
                </div>
            </div>


            <!-- ============================================= -->
            <!-- KPIs -->
            <!-- ============================================= -->

            <div
                id="attendance-kpis"
                data-dashboard-section="attendance"
                style="
                    display: grid;
                    grid-template-columns:
                        repeat(
                            auto-fit,
                            minmax(200px, 1fr)
                        );
                    gap: 15px;
                    margin-bottom: 20px;
                "
            >

                <div
                    class="card"
                    style="padding: 20px;"
                >
                    Loading...
                </div>

            </div>


            <div
                id="assessment-kpis"
                data-dashboard-section="assessment"
                style="
                    display: none;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                "
            ></div>


            <div
                id="finance-kpis"
                data-dashboard-section="finance"
                style="
                    display: none;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 20px;
                "
            ></div>


            <!-- ============================================= -->
            <!-- Executive Attention -->
            <!-- ============================================= -->

            <div
                class="card"
                style="
                    padding: 20px;
                    margin-bottom: 20px;
                "
            >

                <h4 style="margin-top: 0;">
                    Management Action Queue
                </h4>

                <div id="executive-alerts">

                    <i>
                        Loading management information...
                    </i>

                </div>

            </div>


            <!-- ============================================= -->
            <!-- Attendance Management -->
            <!-- ============================================= -->

            <div
                id="attendance-management-container"
                data-dashboard-section="attendance"
                class="card"
                style="
                    padding: 20px;
                    margin-bottom: 20px;
                    display: none;
                "
            >

                <h4 style="margin-top: 0;">
                    Attendance Management
                </h4>

                <div id="attendance-management-content">
                </div>

            </div>


            <!-- ============================================= -->
            <!-- Student Attendance Management -->
            <!-- ============================================= -->

            <div
                id="student-management-container"
                data-dashboard-section="attendance"
                class="card"
                style="
                    padding: 20px;
                    margin-bottom: 20px;
                    display: none;
                "
            >

                <h4 style="margin-top: 0;">
                    Student Attendance Follow-up
                </h4>

                <div id="student-management-content">
                </div>

            </div>


            <!-- ============================================= -->
            <!-- Assessment Operations -->
            <!-- ============================================= -->

            <div
                id="academic-operations-container"
                data-dashboard-section="assessment"
                class="card"
                style="
                    padding: 20px;
                    margin-bottom: 20px;
                    display: none;
                "
            >

                <h4 style="margin-top: 0;">
                    Assessment Operations
                </h4>

                <div id="academic-operations-content">
                </div>

            </div>


            <!-- ============================================= -->
            <!-- Academic Performance -->
            <!-- ============================================= -->

            <div
                id="academic-performance-container"
                data-dashboard-section="assessment"
                class="card"
                style="
                    padding: 20px;
                    margin-bottom: 20px;
                    display: none;
                "
            >

                <h4 style="margin-top: 0;">
                    Academic Performance
                </h4>

                <div id="academic-performance-content">
                </div>

            </div>


            <div
                id="finance-management-container"
                data-dashboard-section="finance"
                class="card"
                style="padding: 20px; margin-bottom: 20px; display: none;"
            >
                <h4 style="margin-top: 0;">Student Fees & Finance</h4>
                <div id="finance-management-content"></div>
            </div>


            <!-- ============================================= -->
            <!-- Insights -->
            <!-- ============================================= -->

            <div
                id="attendance-insights-card"
                data-dashboard-section="attendance"
                class="card"
                style="padding: 10px;"
            >

                <h4 style="padding: 10px;">
                    Attendance Analytics
                </h4>

                <div id="insights-container">

                    <div
                        style="
                            padding: 20px;
                            color: #6c757d;
                        "
                    >
                        Insights dashboard URL
                        has not been configured.
                    </div>

                </div>

            </div>

            <div
                id="assessment-insights-card"
                data-dashboard-section="assessment"
                class="card"
                style="padding: 10px; display: none;"
            >
                <h4 style="padding: 10px;">Assessment Analytics</h4>
                <div id="assessment-insights-container"></div>
            </div>

            <div
                id="finance-insights-card"
                data-dashboard-section="finance"
                class="card"
                style="padding: 10px; display: none;"
            >
                <h4 style="padding: 10px;">Finance Analytics</h4>
                <div id="finance-insights-container"></div>
            </div>

        </div>

    `);


    let activeDashboardSection = 'attendance';

    function setSectionVisibility(selector, visible) {
        const element = $(selector);
        element.attr('data-section-content', visible ? '1' : '0');
        const belongsToActiveSection = (
            element.attr('data-dashboard-section')
            === activeDashboardSection
        );
        element.toggle(Boolean(visible && belongsToActiveSection));
    }

    function showDashboardSection(section) {
        activeDashboardSection = section;
        $('[data-dashboard-section]').hide();
        $(`[data-dashboard-section="${section}"]`)
            .filter('[data-section-content!="0"]')
            .show();
        $(`#${section}-kpis`).css('display', 'grid');
        $('.dashboard-section-tab')
            .removeClass('btn-primary')
            .addClass('btn-default');
        $(`.dashboard-section-tab[data-section="${section}"]`)
            .removeClass('btn-default')
            .addClass('btn-primary');
    }

    $('#dashboard-section-tabs')
        .off('click', '.dashboard-section-tab')
        .on('click', '.dashboard-section-tab', function() {
            showDashboardSection($(this).data('section'));
        });

    showDashboardSection('attendance');


    // =========================================================
    // Utilities
    // =========================================================

    function escapeHtml(value) {

        return $('<div>')
            .text(
                value === null
                || value === undefined
                    ? ''
                    : String(value)
            )
            .html();

    }


    function formatPercent(value) {

        if (
            value === null
            || value === undefined
        ) {
            return 'N/A';
        }

        return `${value}%`;

    }


    function formatNumber(value) {

        if (
            value === null
            || value === undefined
        ) {
            return '0';
        }

        return Number(
            value
        ).toLocaleString();

    }


    function formatMoney(value, currency) {

        const amount = Number(value || 0).toLocaleString(
            undefined,
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );

        return `${currency ? `${currency} ` : ''}${amount}`;

    }


    function statusLabel(status) {

        switch (status) {

            case 'healthy':
                return 'Healthy';

            case 'warning':
                return 'Needs Attention';

            case 'no_data':
                return 'No Data';

            case 'ready':
                return 'Ready';

            case 'incomplete':
                return 'Incomplete';

            case 'data_issue':
                return 'Data Issue';

            case 'improving':
                return 'Improving';

            case 'stable':
                return 'Holding Steady';

            case 'declining':
                return 'Needs Attention';

            case 'mixed':
                return 'Mixed Direction';

            default:
                return '';

        }

    }


    function statusBorder(status) {

        switch (status) {

            case 'healthy':
                return '#28a745';

            case 'warning':
                return '#f0ad4e';

            case 'no_data':
                return '#6c757d';

            case 'ready':
                return '#28a745';

            case 'incomplete':
            case 'data_issue':
                return '#dc3545';

            case 'improving':
                return '#28a745';

            case 'stable':
                return '#007bff';

            case 'declining':
                return '#dc3545';

            case 'mixed':
                return '#f0ad4e';

            default:
                return '#dee2e6';

        }

    }


    function severityBorder(severity) {

        switch (severity) {

            case 'Critical':
                return '#dc3545';

            case 'Action Required':
                return '#fd7e14';

            case 'Warning':
                return '#f0ad4e';

            case 'Information':
                return '#007bff';

            default:
                return '#6c757d';

        }

    }


    function createKpiCard({
        title,
        value,
        subtitle = '',
        status = null
    }) {

        const border =
            statusBorder(
                status
            );

        return `

            <div
                class="card"
                style="
                    padding: 20px;
                    border-left:
                        4px solid ${border};
                "
            >

                <div
                    style="
                        color: #6c757d;
                        font-size: 12px;
                        font-weight: 600;
                        text-transform: uppercase;
                    "
                >
                    ${escapeHtml(title)}
                </div>


                <div
                    style="
                        font-size: 30px;
                        font-weight: 700;
                        margin-top: 8px;
                    "
                >
                    ${escapeHtml(value)}
                </div>


                ${
                    subtitle
                        ? `
                            <div
                                style="
                                    margin-top: 6px;
                                    color: #6c757d;
                                "
                            >
                                ${escapeHtml(
                                    subtitle
                                )}
                            </div>
                        `
                        : ''
                }


                ${
                    status
                        ? `
                            <div
                                style="
                                    margin-top: 6px;
                                    font-size: 12px;
                                    font-weight: 600;
                                "
                            >
                                ${escapeHtml(
                                    statusLabel(
                                        status
                                    )
                                )}
                            </div>
                        `
                        : ''
                }

            </div>

        `;

    }


    // =========================================================
    // School Terms
    // =========================================================

    frappe.call({

        method:
            'frappe.client.get_list',

        args: {

            doctype:
                'School Term',

            fields: [
                'name',
                'academic_year',
                'term',
                'start_date',
                'end_date'
            ],

            order_by:
                'start_date desc',

            limit_page_length:
                50
        },

        callback: function(r) {

            const terms =
                r.message || [];

            const yearSelector =
                $('#academic-year-selector');

            const selector =
                $('#school-term-selector');

            yearSelector.empty();
            selector.empty();


            if (!terms.length) {

                selector.append(`
                    <option value="">
                        No School Terms found
                    </option>
                `);

                return;

            }


            const today =
                frappe.datetime.get_today();


            const currentTerm =
                terms.find(term => {

                    return (
                        term.start_date <= today
                        &&
                        term.end_date >= today
                    );

                });


            const academicYears = [...new Set(terms.map(term => term.academic_year))];
            academicYears.forEach(academicYear => {
                yearSelector.append(`<option value="${escapeHtml(academicYear)}">${escapeHtml(academicYear)}</option>`);
            });

            const selectedAcademicYear = (currentTerm || terms[0]).academic_year;
            yearSelector.val(selectedAcademicYear);

            function loadTermsForAcademicYear(academicYear, preferredTermName) {
                const matchingTerms = terms.filter(term => term.academic_year === academicYear);
                selector.empty();
                matchingTerms.forEach(term => {

                selector.append(`

                    <option
                        value="${escapeHtml(
                            term.name
                        )}"
                    >
                        ${escapeHtml(
                            term.academic_year
                        )}
                        -
                        ${escapeHtml(
                            term.term
                        )}
                    </option>

                `);

                });

                if (!matchingTerms.length) {
                    selector.append(`<option value="">No School Terms for this Academic Year</option>`);
                    $('#term-dates').text('');
                    return;
                }

                const selectedTerm = matchingTerms.find(term => term.name === preferredTermName)
                    || matchingTerms.find(term => term.start_date <= today && term.end_date >= today)
                    || matchingTerms[0];

                selector.val(selectedTerm.name);
                updateTermDates(selectedTerm);
                loadExecutiveSummary(selectedTerm.name);
            }

            loadTermsForAcademicYear(selectedAcademicYear, currentTerm && currentTerm.name);

            yearSelector.on('change', function() {
                loadTermsForAcademicYear($(this).val());
            });


            selector.on(
                'change',
                function() {

                    const termName =
                        $(this).val();


                    const term =
                        terms.find(
                            item =>
                                item.name
                                === termName
                        );


                    if (!term) {
                        return;
                    }


                    updateTermDates(
                        term
                    );


                    loadExecutiveSummary(
                        term.name
                    );

                }
            );

        }

    });


    // =========================================================
    // Term Dates
    // =========================================================

    function updateTermDates(term) {

        $('#term-dates')
            .text(
                `${term.start_date} → ${term.end_date}`
            );

    }


    // =========================================================
    // Load Executive Data
    // =========================================================

    function loadExecutiveSummary(
        schoolTerm
    ) {

        $('#attendance-kpis, #assessment-kpis, #finance-kpis')
            .html(`

                <div
                    class="card"
                    style="padding: 20px;"
                >
                    Loading...
                </div>

            `);

        $('#school-direction-content')
            .html('<i>Comparing this term with the previous School Term...</i>');


        $('#executive-alerts')
            .html(`

                <i>
                    Loading management information...
                </i>

            `);


        setSectionVisibility(
            '#attendance-management-container',
            false
        );


        setSectionVisibility(
            '#student-management-container',
            false
        );


        setSectionVisibility(
            '#academic-operations-container',
            false
        );


        setSectionVisibility(
            '#academic-performance-container',
            false
        );

        setSectionVisibility(
            '#finance-management-container',
            false
        );


        frappe.call({

            method:
                'high_school.high_school.executive_mis.get_executive_summary',

            args: {
                school_term:
                    schoolTerm
            },

            callback: function(r) {

                if (!r.message) {

                    showError(
                        'Unable to load Executive MIS.'
                    );

                    return;

                }


                const data =
                    r.message;


                if (data.error) {

                    showError(
                        data.error
                    );

                    return;

                }


                renderExecutiveMIS(
                    data
                );

            },

            error: function() {

                showError(
                    'An error occurred while loading the Executive MIS.'
                );

            }

        });

    }


    // =========================================================
    // Main Renderer
    // =========================================================

    function renderExecutiveMIS(data) {

        renderSchoolDirection(data);

        renderKpis(
            data
        );

        renderAlerts(
            data.alerts || []
        );

        renderAttendanceManagement(
            data
        );

        renderStudentManagement(
            data
        );

        renderAcademicOperations(
            data
        );

        renderAcademicPerformance(
            data
        );

        renderFinanceManagement(
            data
        );

        renderInsights(data.settings || {});

    }


    // =========================================================
    // School Direction
    // =========================================================

    function renderSchoolDirection(data) {

        const direction = data.direction || {};
        const previous = direction.previous_term;
        const border = statusBorder(direction.status || 'no_data');

        const indicatorCards = (direction.indicators || [])
            .map(indicator => {
                const change = indicator.change;
                const changeText = change === null || change === undefined
                    ? 'No comparable result'
                    : `${change > 0 ? '+' : ''}${change}${indicator.unit || ''}`;
                const arrow = indicator.direction === 'improving'
                    ? '↑'
                    : indicator.direction === 'declining'
                        ? '↓'
                        : indicator.direction === 'stable'
                            ? '→'
                            : '•';

                return `
                    <div
                        style="
                            padding: 14px;
                            border: 1px solid var(--border-color, #dfe2e5);
                            border-radius: 6px;
                        "
                    >
                        <div style="font-weight: 600;">
                            ${escapeHtml(indicator.label)}
                        </div>
                        <div style="font-size: 22px; margin-top: 5px;">
                            ${formatPercent(indicator.current)}
                        </div>
                        <div style="color: #6c757d; margin-top: 4px;">
                            ${arrow} ${escapeHtml(changeText)} from
                            ${formatPercent(indicator.previous)}
                        </div>
                    </div>
                `;
            })
            .join('');

        let narrative = 'There is not enough previous-term information to establish a direction yet.';
        if (direction.status === 'improving') {
            narrative = 'The available attendance, academic, and finance measures are moving in a positive direction.';
        } else if (direction.status === 'declining') {
            narrative = 'The comparable school measures are moving downward and require management action.';
        } else if (direction.status === 'mixed') {
            narrative = 'Some measures are improving while others are declining. Focus on the declining areas.';
        } else if (direction.status === 'stable') {
            narrative = 'The school is holding steady. Review targets to identify the next improvement priority.';
        }

        const financeProgress = direction.finance_progress_to_target;
        const financeText = financeProgress === null || financeProgress === undefined
            ? ''
            : `
                <div style="margin-top: 12px; color: #6c757d;">
                    Fee collection is
                    <b>${Math.abs(financeProgress)} percentage point(s)</b>
                    ${financeProgress >= 0 ? 'above' : 'below'} the school target.
                </div>
            `;

        $('#school-direction-content').html(`
            <div style="border-left: 4px solid ${border}; padding-left: 14px; margin-bottom: 16px;">
                <div style="font-size: 22px; font-weight: 700;">
                    ${escapeHtml(direction.label || 'Not Enough History')}
                </div>
                <div style="margin-top: 5px; color: #6c757d;">
                    ${escapeHtml(narrative)}
                    ${previous ? `Compared with ${escapeHtml(previous.academic_year)} - ${escapeHtml(previous.term)}.` : ''}
                </div>
                ${financeText}
            </div>
            <div
                style="
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
                    gap: 12px;
                "
            >
                ${indicatorCards || `
                    <div class="text-muted">
                        Add results and attendance for an earlier School Term to begin trend comparison.
                    </div>
                `}
            </div>
        `);

        $('#create-board-report-btn').off('click').on('click', function() {
            frappe.call({
                method: 'high_school.high_school.mis.board_report.create_board_report',
                args: {school_term: data.school_term.name},
                freeze: true,
                freeze_message: __('Creating board report snapshot...'),
                callback(r) {
                    if (r.message && r.message.name) {
                        frappe.set_route('Form', 'Executive MIS Board Report', r.message.name);
                    }
                }
            });
        });

    }


    // =========================================================
    // KPIs
    // =========================================================

    function renderKpis(data) {

        const cards = [];


        const daily =
            data.attendance.daily;


        const course =
            data.attendance.course;


        const persistent =
            data.persistent_absence || {};


        const academics =
            data.academics || {};


        const preparation =
            academics.preparation || {};


        const plans =
            preparation.assessment_plans || {};


        const resultSubmission =
            academics.result_submission || {};


        const performanceSummary =
            academics.performance || {};


        const finance =
            data.finance || {};

        const financialOperations = finance.operations || {};
        const payroll = financialOperations.payroll || {};

        const financeHasData = (
            finance.enabled
            && finance.available
            && Number(finance.invoice_count || 0) > 0
        );

        const operationsHaveData = (
            financialOperations.enabled
            && financialOperations.available
        );


        // -----------------------------------------------------
        // Daily Attendance
        // -----------------------------------------------------

        if (daily.enabled) {

            const summary =
                daily.summary;


            cards.push(
                createKpiCard({

                    title:
                        'Daily Attendance',

                    value:
                        formatPercent(
                            summary.attendance_rate
                        ),

                    subtitle:
                        `Target: ${summary.target}%`,

                    status:
                        summary.status

                })
            );


            cards.push(
                createKpiCard({

                    title:
                        'Daily Groups Below Target',

                    value:
                        formatNumber(
                            daily
                                .analysis
                                .groups_below_target_count
                        ),

                    subtitle:
                        'Reliable groups only'

                })
            );

        }


        // -----------------------------------------------------
        // Course Attendance
        // -----------------------------------------------------

        if (course.enabled) {

            const performance =
                course.performance.summary;


            const coverage =
                course.coverage;


            const submission =
                course.submission;


            cards.push(
                createKpiCard({

                    title:
                        'Course Attendance',

                    value:
                        formatPercent(
                            performance
                                .attendance_rate
                        ),

                    subtitle:
                        `Target: ${performance.target}%`,

                    status:
                        performance.status

                })
            );


            cards.push(
                createKpiCard({

                    title:
                        'Course Coverage',

                    value:
                        formatPercent(
                            coverage
                                .coverage_rate
                        ),

                    subtitle:
                        `Target: ${coverage.target}%`,

                    status:
                        coverage.status

                })
            );


            cards.push(
                createKpiCard({

                    title:
                        'Attendance Submission',

                    value:
                        formatPercent(
                            submission
                                .compliance_rate
                        ),

                    subtitle:
                        `Target: ${submission.target}%`,

                    status:
                        submission.status

                })
            );


            cards.push(
                createKpiCard({

                    title:
                        'Missing Classes',

                    value:
                        formatNumber(
                            submission
                                .actionable_missing_sessions
                            ?? submission
                                .missing_sessions
                        ),

                    subtitle:
                        `${submission.resolved_sessions || 0} resolved`
                })
            );


            cards.push(
                createKpiCard({

                    title:
                        'Instructors Below Target',

                    value:
                        formatNumber(
                            submission
                                .teachers_below_target
                        ),

                    subtitle:
                        'Submission compliance'

                })
            );

        }


        // -----------------------------------------------------
        // Persistent Absence
        // -----------------------------------------------------

        cards.push(
            createKpiCard({

                title:
                    'Persistent Absence',

                value:
                    formatNumber(
                        persistent
                            .unique_students_flagged
                        || 0
                    ),

                subtitle:
                    `${formatNumber(persistent.managed_students_count || 0)} managed / resolved`,

                status:
                    (
                        (
                            persistent
                                .unique_students_flagged
                            || 0
                        ) > 0
                            ? 'warning'
                            : 'healthy'
                    )

            })
        );

        const attendanceCards = cards;
        const assessmentCards = [];
        const financeCards = [];


        // -----------------------------------------------------
        // Assessment Operations
        // -----------------------------------------------------

        assessmentCards.push(
            createKpiCard({

                title:
                    'Exam Preparation',

                value:
                    formatPercent(
                        preparation.coverage_rate
                    ),

                subtitle:
                    `Target: ${preparation.target ?? 95}%`,

                status:
                    preparation.status || 'no_data'

            })
        );


        assessmentCards.push(
            createKpiCard({

                title:
                    'Assessment Plan Coverage',

                value:
                    formatPercent(
                        plans.coverage_rate
                    ),

                subtitle:
                    `${formatNumber(plans.created)} of ${formatNumber(plans.expected)} created`,

                status:
                    plans.status || 'no_data'

            })
        );


        assessmentCards.push(
            createKpiCard({

                title:
                    'Result Submission',

                value:
                    formatPercent(
                        resultSubmission.submission_rate
                    ),

                subtitle:
                    `${formatNumber(resultSubmission.overdue_trackers)} overdue plan(s)`,

                status:
                    resultSubmission.status || 'no_data'

            })
        );


        assessmentCards.push(
            createKpiCard({

                title:
                    'School Average',

                value:
                    formatPercent(
                        performanceSummary.school_average
                    ),

                subtitle:
                    `Target: ${data.settings.academic_performance_target ?? 60}%; ${formatNumber(performanceSummary.students_analysed)} student(s) analysed`,

                status:
                    performanceSummary.school_average === null || performanceSummary.school_average === undefined
                        ? 'no_data'
                        : Number(performanceSummary.school_average) < Number(data.settings.academic_performance_target ?? 60)
                            ? 'warning'
                            : 'healthy'

            })
        );


        financeCards.push(
            createKpiCard({
                title: 'Cash & Bank Available',
                value: formatMoney(financialOperations.cash_and_bank, financialOperations.currency || finance.currency),
                subtitle: operationsHaveData ? `Company balance at ${financialOperations.as_of}` : 'Configure School Finance Company',
                status: operationsHaveData ? 'healthy' : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Term Income',
                value: formatMoney(financialOperations.term_income, financialOperations.currency || finance.currency),
                subtitle: financialOperations.income_basis === 'collected_school_term_student_fees'
                    ? `Student fees collected for ${data.school_term?.name || 'selected term'}`
                    : `Scope: ${financialOperations.scope || 'not configured'}`,
                status: operationsHaveData ? 'healthy' : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Term Expenses',
                value: formatMoney(financialOperations.term_expenses, financialOperations.currency || finance.currency),
                subtitle: 'Independent of term income',
                status: operationsHaveData ? financialOperations.status : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Operating Result',
                value: formatMoney(financialOperations.operating_surplus, financialOperations.currency || finance.currency),
                subtitle: `${formatPercent(financialOperations.operating_margin)} margin`,
                status: operationsHaveData
                    ? (Number(financialOperations.operating_surplus || 0) >= 0 ? 'healthy' : 'warning')
                    : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Budget Used',
                value: formatPercent((financialOperations.budget || {}).utilisation_rate),
                subtitle: `${formatMoney((financialOperations.budget || {}).used, financialOperations.currency || finance.currency)} of ${formatMoney((financialOperations.budget || {}).budget_total, financialOperations.currency || finance.currency)}`,
                status: operationsHaveData ? ((financialOperations.budget || {}).status || 'no_data') : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Payroll Processed',
                value: formatMoney(payroll.net_pay, financialOperations.currency || finance.currency),
                subtitle: `${formatNumber(payroll.employee_count)} employee(s); ${formatMoney(payroll.gross_pay, financialOperations.currency || finance.currency)} gross; ${formatMoney(payroll.wage_gl_expense, financialOperations.currency || finance.currency)} posted expense`,
                status: payroll.available
                    ? (payroll.reconciliation_status === 'warning' ? 'warning' : (payroll.status || 'no_data'))
                    : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Payroll Payable',
                value: payroll.payroll_payable_available
                    ? formatMoney(payroll.payroll_payable, financialOperations.currency || finance.currency)
                    : 'Not configured',
                subtitle: 'Remaining salary liability',
                status: payroll.payroll_payable_available
                    ? (Number(payroll.payroll_payable || 0) > 0 ? 'warning' : 'healthy')
                    : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Fee Collection',
                value: formatPercent(finance.collection_rate),
                subtitle: `Target: ${finance.target ?? 90}%`,
                status: financeHasData ? (finance.status || 'no_data') : 'no_data'
            })
        );

        financeCards.push(
            createKpiCard({
                title: 'Outstanding / Overdue Fees',
                value: formatMoney(finance.outstanding, finance.currency),
                subtitle: `${formatMoney(finance.overdue, finance.currency)} overdue across ${formatNumber(finance.overdue_student_count)} student(s)`,
                status: financeHasData
                    ? (Number(finance.overdue_student_count || 0) > 0 ? 'warning' : 'healthy')
                    : 'no_data'
            })
        );


        if (!cards.length) {

            cards.push(
                createKpiCard({

                    title:
                        'Attendance Tracking',

                    value:
                        'Disabled',

                    subtitle:
                        'Configure School MIS Settings'

                })
            );

        }


        $('#attendance-kpis')
            .html(
                attendanceCards.join('')
            );

        $('#assessment-kpis')
            .html(assessmentCards.join(''));

        $('#finance-kpis')
            .html(financeCards.join(''));

        showDashboardSection(activeDashboardSection);

    }


    // =========================================================
    // Executive Alerts
    // =========================================================

    function renderAlerts(alerts) {

        const container =
            $('#executive-alerts');


        if (!alerts.length) {

            container.html(`

                <div
                    style="
                        color: #6c757d;
                        padding: 5px 0;
                    "
                >
                    No configured MIS alert rules are currently triggered.
                    Operational follow-up actions remain available inside each section.
                </div>

            `);

            return;

        }


        const html =
            alerts
                .map(alert => {

                    const border =
                        severityBorder(
                            alert.severity
                        );


                    const message =
                        alert.message
                            ? `

                                <div
                                    style="
                                        margin-top: 8px;
                                    "
                                >
                                    ${escapeHtml(
                                        alert.message
                                    )}
                                </div>

                            `
                            : '';


                    const recommendation =
                        alert.recommended_action
                            ? `

                                <div
                                    style="
                                        margin-top: 10px;
                                    "
                                >

                                    <b>
                                        Recommended Action:
                                    </b>

                                    ${escapeHtml(
                                        alert
                                            .recommended_action
                                    )}

                                </div>

                            `
                            : '';


                    return `

                        <div
                            style="
                                padding: 15px;
                                border-left:
                                    4px solid ${border};
                                background:
                                    var(
                                        --control-bg,
                                        #f8f9fa
                                    );
                                margin-bottom: 12px;
                                border-radius: 4px;
                            "
                        >

                            <div
                                style="
                                    display: flex;
                                    justify-content:
                                        space-between;
                                    gap: 15px;
                                "
                            >

                                <b>
                                    ${escapeHtml(
                                        alert.title
                                    )}
                                </b>


                                <div
                                    style="
                                        font-size: 12px;
                                        font-weight: 600;
                                    "
                                >
                                    ${escapeHtml(
                                        alert.severity
                                    )}
                                </div>

                            </div>


                            <div
                                style="
                                    margin-top: 7px;
                                    color: #6c757d;
                                    font-size: 13px;
                                "
                            >

                                Current:
                                ${escapeHtml(
                                    alert.value
                                )}

                                &nbsp;•&nbsp;

                                Trigger:
                                ${escapeHtml(
                                    alert.operator
                                )}

                                ${escapeHtml(
                                    alert.threshold
                                )}

                            </div>


                            ${message}

                            ${recommendation}

                        </div>

                    `;

                })
                .join('');


        container.html(
            html
        );

    }


    // =========================================================
    // Attendance Management Summary
    // =========================================================

    function renderAttendanceManagement(
        data
    ) {

        const course =
            data.attendance.course;


        if (!course.enabled) {

            setSectionVisibility(
                '#attendance-management-container',
                false
            );

            return;

        }


        const submission =
            course.submission || {};


        const missing =
            submission
                .actionable_missing_sessions
            ?? submission
                .missing_sessions
            ?? 0;


        const incomplete =
            submission
                .actionable_incomplete_sessions
            ?? submission
                .incomplete_sessions
            ?? 0;


        const teachersBelow =
            submission
                .teachers_below_target
            || 0;


        const resolved =
            submission
                .resolved_sessions
            || 0;


        const hasIssues = (
            missing > 0
            ||
            incomplete > 0
        );


        if (!hasIssues) {

            setSectionVisibility(
                '#attendance-management-container',
                false
            );

            return;

        }


        $('#attendance-management-content')
            .html(`

                <div
                    style="
                        display: flex;
                        justify-content:
                            space-between;
                        align-items: center;
                        gap: 20px;
                        flex-wrap: wrap;
                    "
                >

                    <div>

                        <div
                            style="
                                font-size: 15px;
                                font-weight: 600;
                                margin-bottom: 5px;
                            "
                        >
                            Course attendance requires
                            management review
                        </div>


                        <div
                            style="
                                color: #6c757d;
                            "
                        >

                            ${missing}
                            unresolved missing class(es),

                            ${incomplete}
                            unresolved incomplete
                            submission(s).

                            ${
                                resolved > 0
                                    ? `
                                        ${resolved}
                                        historical issue(s)
                                        have been resolved.
                                    `
                                    : ''
                            }

                        </div>

                    </div>


                    <button
                        id="investigate-attendance-btn"
                        class="btn btn-primary btn-sm"
                    >
                        Investigate Attendance
                    </button>

                    <button id="attendance-reminders-btn" class="btn btn-default btn-sm">
                        ${escapeHtml((data.settings || {}).attendance_reminder_action || 'Email Reminder')}
                    </button>

                </div>

            `);


        setSectionVisibility(
            '#attendance-management-container',
            true
        );


        $('#investigate-attendance-btn')
            .off('click')
            .on(
                'click',
                function() {

                    showAttendanceInvestigation(
                        course,
                        data.school_term.name
                    );

                }
            );

        $('#attendance-reminders-btn').off('click').on('click', function() {
            showAttendanceReminderPreview(data.school_term.name);
        });

    }


    function showAttendanceReminderPreview(schoolTerm) {
        frappe.call({
            method: 'high_school.high_school.mis.actions.get_attendance_reminder_preview',
            args: {school_term: schoolTerm}, freeze: true,
            freeze_message: __('Preparing attendance follow-up...'),
            callback(r) {
                const preview = r.message || {};
                const rows = (preview.recipients || []).map(recipient => `
                    <tr><td><input type="checkbox" class="attendance-reminder-recipient" data-user="${escapeHtml(recipient.user)}" checked></td>
                    <td>${escapeHtml(recipient.full_name)}</td><td>${escapeHtml(recipient.email)}</td>
                    <td>${formatNumber(recipient.missing_count)}</td><td>${formatNumber(recipient.incomplete_count)}</td></tr>
                `).join('');
                const dialog = new frappe.ui.Dialog({
                    title: __(preview.action || 'Attendance Follow-up'), size: 'large',
                    fields: [{fieldname:'preview', fieldtype:'HTML'}],
                    primary_action_label: __('Queue Selected Emails'),
                    primary_action() {
                        const users = dialog.$wrapper.find('.attendance-reminder-recipient:checked').map(function(){return $(this).data('user');}).get();
                        if (!users.length) { frappe.msgprint(__('Select at least one instructor.')); return; }
                        frappe.confirm(__('Queue {0} attendance follow-up email(s)?', [users.length]), () => frappe.call({
                            method: 'high_school.high_school.mis.actions.send_attendance_reminders',
                            args: {school_term: schoolTerm, selected_users: JSON.stringify(users)},
                            freeze: true, freeze_message: __('Queueing attendance follow-up...'),
                            callback(sendResult) { if (!sendResult.exc) { dialog.hide(); frappe.msgprint(__('Attendance follow-up emails queued.')); } }
                        }));
                    }
                });
                dialog.fields_dict.preview.$wrapper.html(`
                    <p class="text-muted">Only instructors with at least ${formatNumber(preview.threshold)} unresolved historical classes are listed. Action: <b>${escapeHtml(preview.action)}</b>.</p>
                    <table class="table table-bordered"><thead><tr><th>Send</th><th>Instructor</th><th>Email</th><th>Missing</th><th>Incomplete</th></tr></thead>
                    <tbody>${rows || '<tr><td colspan="5">No instructor currently meets the configured threshold.</td></tr>'}</tbody></table>
                `);
                if (!(preview.recipients || []).length) dialog.disable_primary_action();
                dialog.show();
            }
        });
    }

    // =========================================================
    // Attendance Investigation
    // =========================================================

    function showAttendanceInvestigation(
        course,
        schoolTerm
    ) {

        const submission =
            course.submission || {};


        const teachers =
            submission.teachers || [];


        const sessions =
            course.attention_sessions || [];


        // =====================================================
        // Teacher compliance
        // =====================================================

        const teacherRows =
            teachers

                .filter(
                    teacher =>
                        teacher.status
                        === 'warning'
                )

                .map(teacher => `

                    <tr data-instructor="${escapeHtml(teacher.instructor || '')}">

                        <td>
                            ${escapeHtml(
                                teacher.instructor_name
                                || teacher.instructor
                            )}
                        </td>

                        <td>
                            ${teacher.expected_sessions}
                        </td>

                        <td>
                            ${teacher.complete_sessions}
                        </td>

                        <td>
                            ${teacher.missing_sessions}
                        </td>

                        <td>
                            ${teacher.incomplete_sessions}
                        </td>

                        <td>
                            ${formatPercent(
                                teacher.compliance_rate
                            )}
                        </td>

                    </tr>

                `)

                .join('');


        // =====================================================
        // Unresolved sessions
        // =====================================================

        const sessionRows =
            sessions

                .map(session => {

                    const issue =
                        session.management_issue || {};


                    const issueStatus =
                        issue.status
                        || 'Not Reviewed';


                    return `

                        <tr data-instructor="${escapeHtml(session.instructor || '')}">

                            <td>
                                ${escapeHtml(
                                    session.schedule_date
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    session.course
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    session.student_group
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    session.instructor_name
                                    || session.instructor
                                    || 'Unassigned'
                                )}
                            </td>

                            <td>
                                ${session.expected_students}
                            </td>

                            <td>
                                ${session.recorded_students}
                            </td>

                            <td>
                                ${formatPercent(
                                    session.coverage_rate
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    session.submission_status
                                )}
                            </td>

                            <td>
                                ${escapeHtml(
                                    issueStatus
                                )}
                            </td>

                            <td>

                                <button
                                    class="
                                        btn
                                        btn-xs
                                        btn-default
                                        manage-attendance-issue
                                    "
                                    data-course-schedule="${
                                        escapeHtml(
                                            session.course_schedule
                                        )
                                    }"
                                >
                                    ${
                                        issue.name
                                            ? 'Manage'
                                            : 'Review'
                                    }
                                </button>

                            </td>

                        </tr>

                    `;

                })

                .join('');


        const dialog =
            new frappe.ui.Dialog({

                title:
                    'Attendance Investigation',

                size:
                    'extra-large',

                fields: [

                    {
                        fieldname:
                            'details',

                        fieldtype:
                            'HTML'
                    }

                ]

            });


        dialog.fields_dict
            .details
            .$wrapper
            .html(`

                <div
                    style="
                        margin-bottom: 15px;
                        color: #6c757d;
                    "
                >
                    Historical attendance should not be
                    fabricated. Review each unresolved
                    session and record the appropriate
                    management outcome.
                </div>

                <div style="max-width: 320px; margin-bottom: 15px;">
                    <label>Instructor</label>
                    <select id="attendance-instructor-filter" class="form-control">
                        <option value="">All instructors</option>
                        ${teachers.map(teacher => `<option value="${escapeHtml(teacher.instructor || '')}">${escapeHtml(teacher.instructor_name || teacher.instructor)}</option>`).join('')}
                    </select>
                </div>


                <h5>
                    Scheduled Classes Requiring Attention
                </h5>


                <div
                    style="
                        overflow-x: auto;
                        margin-bottom: 30px;
                    "
                >

                    <table
                        class="
                            table
                            table-bordered
                            table-hover
                        "
                    >

                        <thead>

                            <tr>
                                <th>Date</th>
                                <th>Course</th>
                                <th>Group</th>
                                <th>Instructor</th>
                                <th>Expected</th>
                                <th>Recorded</th>
                                <th>Coverage</th>
                                <th>Attendance Status</th>
                                <th>Management Status</th>
                                <th>Action</th>
                            </tr>

                        </thead>


                        <tbody>

                            ${
                                sessionRows
                                ||
                                `
                                    <tr>
                                        <td colspan="10">
                                            No unresolved sessions
                                            currently require review.
                                        </td>
                                    </tr>
                                `
                            }

                        </tbody>

                    </table>

                </div>


                <h5>
                    Instructor Submission Performance
                </h5>


                <div style="overflow-x: auto;">

                    <table
                        class="
                            table
                            table-bordered
                            table-hover
                        "
                    >

                        <thead>

                            <tr>
                                <th>Instructor</th>
                                <th>Expected</th>
                                <th>Complete</th>
                                <th>Missing</th>
                                <th>Incomplete</th>
                                <th>Compliance</th>
                            </tr>

                        </thead>


                        <tbody>

                            ${
                                teacherRows
                                ||
                                `
                                    <tr>
                                        <td colspan="6">
                                            No instructors are
                                            currently below target.
                                        </td>
                                    </tr>
                                `
                            }

                        </tbody>

                    </table>

                </div>

            `);


        dialog.show();

        dialog.$wrapper.find('#attendance-instructor-filter').on('change', function() {
            const instructor = String($(this).val() || '');
            dialog.$wrapper.find('tbody tr[data-instructor]').each(function() {
                $(this).toggle(!instructor || String($(this).data('instructor')) === instructor);
            });
        });


        // =====================================================
        // Manage Issue
        // =====================================================

        dialog.$wrapper
            .off(
                'click',
                '.manage-attendance-issue'
            )
            .on(
                'click',
                '.manage-attendance-issue',

                function() {

                    const courseSchedule =
                        $(this).data(
                            'course-schedule'
                        );


                    frappe.call({

                        method:
                            'high_school.high_school.management_mis.get_or_create_course_attendance_issue',

                        args: {
                            course_schedule:
                                courseSchedule,

                            school_term:
                                schoolTerm
                        },

                        freeze:
                            true,

                        freeze_message:
                            __(
                                'Opening management issue...'
                            ),

                        callback(r) {

                            if (
                                !r.message
                                ||
                                !r.message.name
                            ) {
                                return;
                            }


                            dialog.hide();


                            frappe.set_route(
                                'Form',
                                'MIS Issue',
                                r.message.name
                            );

                        }

                    });

                }
            );

    } 


    // =========================================================
    // Persistent Absence Management
    // =========================================================

    function renderStudentManagement(
        data
    ) {

        const persistent =
            data.persistent_absence || {};


        const count =
            persistent
                .unique_students_flagged
            || 0;

        const interventions = data.interventions || {};
        const attendancePlanCount = Number(interventions.attendance_open || 0);
        const attendanceRows = (interventions.items || [])
            .filter(plan => plan.intervention_type === 'Attendance')
            .slice(0, 10)
            .map(plan => `
                <tr>
                    <td>${escapeHtml(plan.student_name || plan.student)}</td>
                    <td>${escapeHtml(plan.course || '')}</td>
                    <td>${escapeHtml(plan.student_group || '')}</td>
                    <td>${escapeHtml(plan.instructor || '')}</td>
                    <td>${escapeHtml(plan.status || '')}</td>
                    <td>${formatNumber(plan.post_plan_absence_count || 0)}</td>
                    <td><button class="btn btn-xs btn-default open-attendance-intervention" data-name="${escapeHtml(plan.name)}">Open</button></td>
                </tr>
            `).join('');


        $('#student-management-content')
            .html(`

                <div
                    style="
                        display: flex;
                        justify-content:
                            space-between;
                        align-items: center;
                        gap: 20px;
                        flex-wrap: wrap;
                    "
                >

                    <div>

                        <div
                            style="
                                font-size: 15px;
                                font-weight: 600;
                                margin-bottom: 5px;
                            "
                        >
                            Attendance intervention management
                        </div>


                        <div
                            style="
                                color: #6c757d;
                            "
                        >

                            ${count} student(s) currently exceed the whole-term persistent-absence threshold.
                            ${attendancePlanCount} course-specific attendance plan(s) remain active.

                        </div>

                    </div>


                    <button id="refresh-attendance-interventions-btn" class="btn btn-primary btn-sm">
                        Detect / Refresh Course Plans
                    </button>

                    <button
                        id="open-student-follow-ups-btn"
                        class="btn btn-default btn-sm"
                    >
                        Open Attendance Plans
                    </button>

                </div>

                <div style="overflow-x:auto; margin-top:16px;">
                    <table class="table table-bordered table-hover">
                        <thead><tr><th>Student</th><th>Course</th><th>Group</th><th>Instructor</th><th>Status</th><th>New Absences</th><th>Action</th></tr></thead>
                        <tbody>${attendanceRows || '<tr><td colspan="7">No active course-attendance intervention plans for this term.</td></tr>'}</tbody>
                    </table>
                </div>

            `);


        setSectionVisibility(
            '#student-management-container',
            true
        );


        $('#refresh-attendance-interventions-btn').off('click').on('click', function() {
            frappe.call({
                method: 'high_school.high_school.student_interventions.refresh_intervention_plans',
                args: {school_term: data.school_term.name},
                freeze: true,
                freeze_message: __('Checking course-attendance evidence...'),
                callback(r) {
                    if (!r.exc) loadDashboard();
                }
            });
        });

        $('#student-management-content').off('click', '.open-attendance-intervention').on('click', '.open-attendance-intervention', function() {
            frappe.set_route('Form', 'Student Intervention Plan', $(this).data('name'));
        });

        $('#open-student-follow-ups-btn')
            .off('click')
            .on('click', function() {
                frappe.set_route(
                    'List',
                    'Student Intervention Plan',
                    {school_term: data.school_term.name, intervention_type: 'Attendance'}
                );
            });

    }

    // =========================================================
    // Assessment Operations
    // =========================================================

    function renderAcademicOperations(data) {

        const academics = data.academics || {};
        const preparation = academics.preparation || {};
        const plans = preparation.assessment_plans || {};
        const results = academics.result_submission || {};
        const cycles = academics.cycles || [];
        const interventions = data.interventions || {};
        const academicOutcomes = interventions.academic_outcomes || {};

        const cycleNames = cycles.length
            ? cycles
                .map(cycle => escapeHtml(
                    cycle.cycle_name || cycle.name
                ))
                .join(', ')
            : 'No examination cycle configured';

        const attentionCount =
            Number(preparation.outstanding_requirements || 0)
            + Number(results.outstanding_due_trackers || 0)
            + Number(results.awaiting_plan_submission || 0)
            + Number(results.instructor_mapping_errors || 0);

        const academicPlanRows = (interventions.items || [])
            .filter(plan => plan.intervention_type === 'Academic')
            .slice(0, 10)
            .map(plan => `
                <tr>
                    <td>${escapeHtml(plan.student_name || plan.student)}</td>
                    <td>${escapeHtml(plan.course || '')}</td>
                    <td>${escapeHtml(plan.instructor || '')}</td>
                    <td>${formatPercent(plan.baseline_value)}</td>
                    <td>${formatPercent(plan.baseline_overall_percentage)}</td>
                    <td>${formatNumber(plan.consecutive_low_periods || 0)}</td>
                    <td>${escapeHtml(plan.status)}</td>
                    <td>${escapeHtml(plan.assigned_to || '')}</td>
                    <td><button class="btn btn-xs btn-default open-student-intervention" data-name="${escapeHtml(plan.name)}">Open</button></td>
                </tr>
            `).join('');

        $('#academic-operations-content').html(`

            <div
                style="
                    color: #6c757d;
                    margin-bottom: 16px;
                "
            >
                ${formatNumber(academics.cycle_count || 0)} cycle(s):
                ${cycleNames}
            </div>

            <div
                style="
                    display: grid;
                    grid-template-columns:
                        repeat(auto-fit, minmax(220px, 1fr));
                    gap: 14px;
                    margin-bottom: 18px;
                "
            >

                ${createKpiCard({
                    title: 'Exam Requirements Ready',
                    value: `${formatNumber(preparation.fully_ready_requirements)} / ${formatNumber(preparation.total_requirements)}`,
                    subtitle: `${formatNumber(preparation.overdue_requirements)} overdue`,
                    status: preparation.status || 'no_data'
                })}

                ${createKpiCard({
                    title: 'Assessment Plans Created',
                    value: `${formatNumber(plans.created)} / ${formatNumber(plans.expected)}`,
                    subtitle: `${formatNumber(plans.missing)} missing`,
                    status: plans.status || 'no_data'
                })}

                ${createKpiCard({
                    title: 'Due Results Complete',
                    value: `${formatNumber(results.complete_due_trackers)} / ${formatNumber(results.due_trackers)}`,
                    subtitle: `${formatNumber(results.missing_students_due)} unresolved student result(s)`,
                    status: results.status || 'no_data'
                })}

                ${createKpiCard({
                    title: 'Teachers Outstanding',
                    value: formatNumber(results.teachers_outstanding),
                    subtitle: `${formatNumber(results.instructor_mapping_errors)} instructor mapping error(s)`,
                    status: (
                        Number(results.teachers_outstanding || 0)
                        + Number(results.instructor_mapping_errors || 0)
                    ) > 0 ? 'warning' : 'healthy'
                })}

                ${createKpiCard({
                    title: 'Academic Intervention Plans',
                    value: formatNumber(interventions.academic_open || 0),
                    subtitle: `${formatNumber(interventions.overdue || 0)} overdue / escalated across all plan types`,
                    status: Number(interventions.overdue || 0) > 0 ? 'warning' : 'healthy'
                })}

                ${createKpiCard({
                    title: 'Outcome Since Previous Term',
                    value: academicOutcomes.evaluated_students
                        ? `${formatNumber(academicOutcomes.improved_students)} improved / ${formatNumber(academicOutcomes.not_improved_students)} not improved`
                        : 'N/A',
                    subtitle: academicOutcomes.average_change === null || academicOutcomes.average_change === undefined
                        ? 'Term 1 establishes the baseline'
                        : `${academicOutcomes.average_change >= 0 ? '+' : ''}${formatNumber(academicOutcomes.average_change)} percentage points on average`,
                    status: Number(academicOutcomes.not_improved_students || 0) > 0 ? 'warning' : (academicOutcomes.evaluated_students ? 'healthy' : 'no_data')
                })}

            </div>

            <div
                style="
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                "
            >

                <button
                    id="review-academic-attention-btn"
                    class="btn btn-primary btn-sm"
                    ${attentionCount ? '' : 'disabled'}
                >
                    Review ${formatNumber(attentionCount)} Attention Item(s)
                </button>

                ${(frappe.user.has_role('Education Manager') || frappe.user.has_role('System Manager')) ? `
                    <button id="open-bulk-assessment-plan-tool-btn" class="btn btn-primary btn-sm">
                        Bulk Assessment Plans
                    </button>
                ` : ''}

                <button
                    id="email-assessment-reminders-btn"
                    class="btn btn-default btn-sm"
                    ${attentionCount ? '' : 'disabled'}
                >
                    Email Teachers / HODs
                </button>

                <button id="refresh-student-interventions-btn" class="btn btn-primary btn-sm">
                    Detect / Refresh Student Plans
                </button>

                <button id="open-academic-interventions-btn" class="btn btn-default btn-sm">
                    Open Academic Plans
                </button>

				<button id="open-average-batch-performance-btn" class="btn btn-default btn-sm">
					Average Performance by Batch
				</button>

                ${!Number(academics.cycle_count || 0) ? `
                    <button id="create-school-examination-cycle-btn" class="btn btn-primary btn-sm">
                        Create School Examination Cycle
                    </button>
                ` : ''}

            </div>

            <div style="margin-top:18px;">
                <h5>Student Academic Intervention Workflow</h5>
                <div class="text-muted" style="margin-bottom:8px;">
                    Low overall result → one plan for each weak course → scheduled instructor action plan → next official term summary automatically measures improvement or escalation.
                </div>
                <div style="overflow-x:auto"><table class="table table-bordered table-hover">
                    <thead><tr><th>Student</th><th>Course</th><th>Instructor</th><th>Course Baseline</th><th>Overall Baseline</th><th>Low Terms</th><th>Status</th><th>Responsible User</th><th>Action</th></tr></thead>
                    <tbody>${academicPlanRows || '<tr><td colspan="9">No active academic intervention plans for this term.</td></tr>'}</tbody>
                </table></div>
            </div>

        `);

        setSectionVisibility(
            '#academic-operations-container',
            true
        );

        $('#review-academic-attention-btn')
            .off('click')
            .on('click', function() {
                showAcademicAttentionDialog(academics);
            });

        $('#open-bulk-assessment-plan-tool-btn').off('click').on('click', function() {
            frappe.route_options = {
                academic_year: data.school_term.academic_year,
                school_term: data.school_term.name
            };
            frappe.set_route('bulk-assessment-plan-tool');
        });

        $('#email-assessment-reminders-btn')
            .off('click')
            .on('click', function() {
                showAssessmentReminderPreview(
                    data.school_term.name
                );
            });

        $('#refresh-student-interventions-btn').off('click').on('click', function() {
            frappe.call({
                method: 'high_school.high_school.student_interventions.refresh_intervention_plans',
                args: {school_term: data.school_term.name},
                freeze: true,
                freeze_message: __('Checking academic and attendance evidence...'),
                callback(r) {
                    if (r.exc) return;
                    const result = r.message || {};
                    frappe.msgprint({
                        title: __('Student Plans Refreshed'),
                        indicator: 'green',
                        message: __('Refreshed {0} academic and {1} attendance plan result(s).', [
                            (result.academic || []).length,
                            (result.attendance || []).length
                        ])
                    });
                    loadDashboard();
                }
            });
        });

        $('#open-academic-interventions-btn').off('click').on('click', function() {
            frappe.set_route('List', 'Student Intervention Plan', {
                school_term: data.school_term.name,
                intervention_type: 'Academic'
            });
        });

		$('#open-average-batch-performance-btn').off('click').on('click', function() {
			frappe.route_options = {
				academic_year: data.school_term.academic_year,
				school_term: data.school_term.name
			};
			frappe.set_route('query-report', 'Average Performance per Student Batch');
		});

        $('#academic-operations-content').off('click', '.open-student-intervention').on('click', '.open-student-intervention', function() {
            frappe.set_route('Form', 'Student Intervention Plan', $(this).data('name'));
        });

        $('#create-school-examination-cycle-btn').off('click').on('click', function() {
            frappe.route_options = {school_term: data.school_term.name, academic_year: data.school_term.academic_year};
            frappe.new_doc('School Examination Cycle');
        });

    }


    function showAssessmentReminderPreview(schoolTerm) {

        frappe.call({
            method: 'high_school.high_school.mis.actions.get_assessment_reminder_preview',
            args: {school_term: schoolTerm},
            freeze: true,
            freeze_message: __('Preparing teacher reminders...'),
            callback(r) {
                const preview = r.message || {};
                const recipients = preview.recipients || [];

                const rows = recipients.map(recipient => `
                    <tr>
                        <td>
                            <input
                                type="checkbox"
                                class="assessment-reminder-recipient"
                                data-user="${escapeHtml(recipient.user)}"
                                checked
                            >
                        </td>
                        <td>${escapeHtml(recipient.full_name)}</td>
                        <td>${escapeHtml(recipient.email)}</td>
                        <td>${formatNumber(recipient.item_count)}</td>
                        <td>${escapeHtml(
                            (recipient.items || [])
                                .map(item => `${item.course || ''}: ${item.issues || ''}`)
                                .join('; ')
                        )}</td>
                    </tr>
                `).join('');

                const dialog = new frappe.ui.Dialog({
                    title: __('Email Assessment Reminders'),
                    size: 'extra-large',
                    fields: [{fieldname: 'preview', fieldtype: 'HTML'}],
                    primary_action_label: __('Queue Selected Emails'),
                    primary_action() {
                        const selectedUsers = dialog.$wrapper
                            .find('.assessment-reminder-recipient:checked')
                            .map(function() { return $(this).data('user'); })
                            .get();

                        if (!selectedUsers.length) {
                            frappe.msgprint(__('Select at least one recipient.'));
                            return;
                        }

                        frappe.confirm(
                            __('Queue reminder emails for {0} selected recipient(s)?', [selectedUsers.length]),
                            () => frappe.call({
                                method: 'high_school.high_school.mis.actions.send_assessment_reminders',
                                args: {
                                    school_term: schoolTerm,
                                    selected_users: JSON.stringify(selectedUsers)
                                },
                                freeze: true,
                                freeze_message: __('Queueing assessment reminders...'),
                                callback(sendResult) {
                                    if (sendResult.exc) return;
                                    const result = sendResult.message || {};
                                    dialog.hide();
                                    frappe.msgprint({
                                        title: __('Assessment Reminders Queued'),
                                        indicator: 'green',
                                        message: __('Queued {0} email(s) covering {1} attention item(s).', [
                                            result.recipient_count || 0,
                                            result.item_count || 0
                                        ])
                                    });
                                }
                            })
                        );
                    }
                });

                dialog.fields_dict.preview.$wrapper.html(`
                    <div class="text-muted" style="margin-bottom: 12px;">
                        Review the automatically resolved recipients before sending.
                        ${formatNumber(preview.items_without_recipient || 0)} item(s)
                        have no valid teacher/HOD email and will not be sent.
                    </div>
                    <div style="overflow-x: auto;">
                        <table class="table table-bordered table-hover">
                            <thead>
                                <tr>
                                    <th>Send</th>
                                    <th>Teacher / HOD</th>
                                    <th>Email</th>
                                    <th>Items</th>
                                    <th>Summary</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows || '<tr><td colspan="5">No valid reminder recipients were found.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                `);

                if (!recipients.length) {
                    dialog.disable_primary_action();
                }
                dialog.show();
            }
        });

    }


    function showAcademicAttentionDialog(academics) {

        const preparation = academics.preparation || {};
        const results = academics.result_submission || {};

        const preparationRows = (
            preparation.attention_items || []
        ).map(item => `
            <tr>
                <td>Exam Preparation</td>
                <td>${escapeHtml(item.cycle_name || item.examination_cycle)}</td>
                <td>${escapeHtml(item.course)}</td>
                <td>${escapeHtml(item.student_batch)}</td>
                <td>${escapeHtml((item.attention_reasons || []).join(', '))}</td>
                <td>
                    ${item.requirement ? `
                        <button
                            class="btn btn-xs btn-default open-exam-requirement"
                            data-name="${escapeHtml(item.requirement)}"
                        >Open</button>
                    ` : ''}
                </td>
            </tr>
        `);

        const resultRows = (
            results.attention_items || []
        ).map(item => `
            <tr>
                <td>Result Submission</td>
                <td>${escapeHtml(item.examination_cycle)}</td>
                <td>${escapeHtml(item.course)}</td>
                <td>${escapeHtml(item.student_group)}</td>
                <td>${escapeHtml(item.attention_reason)}</td>
                <td>
                    ${item.name ? `
                        <button
                            class="btn btn-xs btn-default open-result-tracker"
                            data-name="${escapeHtml(item.name)}"
                        >Open</button>
                    ` : ''}
                </td>
            </tr>
        `);

        const rows = preparationRows
            .concat(resultRows)
            .join('');

        const dialog = new frappe.ui.Dialog({
            title: 'Assessment Attention',
            size: 'extra-large',
            fields: [{
                fieldname: 'details',
                fieldtype: 'HTML'
            }]
        });

        dialog.fields_dict.details.$wrapper.html(`
            <div style="overflow-x: auto;">
                <table class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th>Area</th>
                            <th>Cycle</th>
                            <th>Course</th>
                            <th>Group / Batch</th>
                            <th>Reason</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows || `
                            <tr>
                                <td colspan="6">
                                    No assessment items currently require attention.
                                </td>
                            </tr>
                        `}
                    </tbody>
                </table>
            </div>
        `);

        dialog.$wrapper
            .off('click', '.open-exam-requirement')
            .on('click', '.open-exam-requirement', function() {
                dialog.hide();
                frappe.set_route(
                    'Form',
                    'Exam Paper Requirement',
                    $(this).data('name')
                );
            });

        dialog.$wrapper
            .off('click', '.open-result-tracker')
            .on('click', '.open-result-tracker', function() {
                dialog.hide();
                frappe.set_route(
                    'Form',
                    'Assessment Result Submission Tracker',
                    $(this).data('name')
                );
            });

        dialog.show();

    }


    // =========================================================
    // Academic Performance
    // =========================================================

    function renderAcademicPerformance(data) {

        const performance = (
            data.academics || {}
        ).performance || {};

        const setup = performance.setup || {};

        if (!performance.available) {

            $('#academic-performance-content').html(`
                <div style="color: #6c757d; margin-bottom: 14px;">
                    No School Performance Period has been configured
                    for this term yet. ${formatNumber(setup.missing_group_count || 0)}
                    active Batch-based main group(s) still need a period.
                </div>
                <button
                    id="setup-performance-periods-btn"
                    class="btn btn-primary btn-sm"
                >
                    Set Up Performance Periods
                </button>
            `);

            setSectionVisibility(
                '#academic-performance-container',
                true
            );

            $('#setup-performance-periods-btn')
                .off('click')
                .on('click', function() {
                    frappe.route_options = {
                        academic_year: data.school_term.academic_year,
                        school_term: data.school_term.name
                    };
                    frappe.set_route('school-performance-period-setup');
                });

            return;

        }

        const groupRows = (performance.groups || [])
            .map(group => `
                <tr>
                    <td>${escapeHtml(group.student_group)}</td>
                    <td>${formatNumber(group.students)}</td>
                    <td>${formatNumber(group.complete_students)}</td>
                    <td>${formatNumber(group.incomplete_students)}</td>
                    <td>${formatPercent(group.average)}</td>
                    <td>${formatPercent(group.highest)}</td>
                    <td>${formatPercent(group.lowest)}</td>
                    <td>
                        <button
                            class="btn btn-xs btn-default open-merit-list"
                            data-period="${escapeHtml(group.performance_period)}"
                        >
                            Merit List
                        </button>
                    </td>
                </tr>
            `)
            .join('');

        const configurationWarning = (
            Number(performance.duplicate_students || 0) > 0
            || (performance.duplicate_group_periods || []).length > 0
        ) ? `
            <div class="alert alert-danger" style="margin-bottom: 15px;">
                Performance configuration needs review:
                ${formatNumber(performance.duplicate_students || 0)} student(s)
                appear in more than one period, and
                ${formatNumber((performance.duplicate_group_periods || []).length)}
                group(s) have duplicate periods.
            </div>
        ` : '';

        const setupWarning = !setup.complete ? `
            <div class="alert alert-warning" style="margin-bottom: 15px;">
                Performance Period setup is incomplete:
                <b>${formatNumber(setup.covered_group_count || 0)}</b> of
                <b>${formatNumber(setup.expected_group_count || 0)}</b>
                active Batch-based main Student Groups are covered.
                Missing: ${escapeHtml(
                    (setup.missing_groups || [])
                        .map(row => row.student_group)
                        .join(', ') || 'group detection requires review'
                )}.
            </div>
        ` : '';

        $('#academic-performance-content').html(`

            ${configurationWarning}
            ${setupWarning}

            <div
                style="
                    display: flex;
                    gap: 22px;
                    flex-wrap: wrap;
                    margin-bottom: 16px;
                    color: #6c757d;
                "
            >
                <span>
                    <b>${formatNumber(performance.students_analysed)}</b>
                    student(s) analysed
                </span>
                <span>
                    <b>${formatNumber(performance.complete_students)}</b>
                    complete
                </span>
                <span>
                    <b>${formatNumber(performance.incomplete_students)}</b>
                    incomplete
                </span>
                <span>
                    School average:
                    <b>${formatPercent(performance.school_average)}</b>
                </span>
            </div>

            <div style="overflow-x: auto; margin-bottom: 14px;">
                <table class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th>Student Group</th>
                            <th>Students</th>
                            <th>Complete</th>
                            <th>Incomplete</th>
                            <th>Average</th>
                            <th>Highest</th>
                            <th>Lowest</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${groupRows || `
                            <tr>
                                <td colspan="8">
                                    No performance summaries have been generated.
                                </td>
                            </tr>
                        `}
                    </tbody>
                </table>
            </div>

            <button
                id="open-performance-periods-btn"
                class="btn btn-default btn-sm"
            >
                Open Performance Periods
            </button>

            <button id="open-bulk-report-card-tool-btn" class="btn btn-primary btn-sm" style="margin-left:6px;">
                Bulk Summaries & Report Cards
            </button>

            ${!setup.complete ? `
                <button
                    id="setup-missing-performance-periods-btn"
                    class="btn btn-primary btn-sm"
                    style="margin-left: 6px;"
                >
                    Set Up Missing Performance Periods
                </button>
            ` : ''}

        `);

        setSectionVisibility(
            '#academic-performance-container',
            true
        );

        $('#open-performance-periods-btn')
            .off('click')
            .on('click', function() {
                frappe.set_route(
                    'List',
                    'School Performance Period',
                    {school_term: data.school_term.name}
                );
            });

        $('#open-bulk-report-card-tool-btn').off('click').on('click', function() {
            frappe.route_options = {
                academic_year: data.school_term.academic_year,
                school_term: data.school_term.name
            };
            frappe.set_route('student-report-card-tool');
        });

        $('#setup-missing-performance-periods-btn')
            .off('click')
            .on('click', function() {
                frappe.route_options = {
                    academic_year: data.school_term.academic_year,
                    school_term: data.school_term.name
                };
                frappe.set_route('school-performance-period-setup');
            });

        $('#academic-performance-content')
            .off('click', '.open-merit-list')
            .on('click', '.open-merit-list', function() {
                frappe.set_route(
                    'query-report',
                    'School Performance Merit List',
                    {performance_period: $(this).data('period')}
                );
            });

    }


    // =========================================================
    // Student Fees & Finance
    // =========================================================

    function renderFinanceManagement(data) {

        const finance = data.finance || {};
        const operations = finance.operations || {};
        const budget = operations.budget || {};
        const payroll = operations.payroll || {};
        const fiscalProfitAndLoss = operations.fiscal_profit_and_loss || {};
        const fundRequests = operations.fund_requests || {};
        const container = $('#finance-management-content');
        const currency = operations.currency || finance.currency;

        let operationsHtml = `
            <div class="alert alert-warning">
                ${escapeHtml(operations.message || 'Whole-school finance is disabled in School MIS Settings.')}
                <button class="btn btn-xs btn-default open-finance-settings" style="margin-left:8px;">Open Settings</button>
            </div>
        `;

        if (operations.enabled && operations.available) {
            const diagnosticRows = (operations.diagnostics || [])
                .map(message => `<li>${escapeHtml(message)}</li>`).join('');
            const incomeRows = (operations.income_breakdown || []).map(row => `
                <tr><td>Income</td><td>${escapeHtml(row.category || '')}</td><td>${escapeHtml(row.account)}</td><td>${escapeHtml(row.cost_center || '')}</td><td class="text-right">${formatMoney(row.amount, currency)}</td></tr>
            `).join('');
            const expenseRows = (operations.expense_breakdown || []).map(row => `
                <tr><td>Expense</td><td>${escapeHtml(row.category || '')}</td><td>${escapeHtml(row.account)}</td><td>${escapeHtml(row.cost_center || '')}</td><td class="text-right">${formatMoney(row.amount, currency)}</td></tr>
            `).join('');
            const fiscalIncomeRows = (fiscalProfitAndLoss.income_breakdown || []).map(row => `
                <tr><td>Income</td><td>${escapeHtml(row.category || '')}</td><td>${escapeHtml(row.account)}</td><td>${escapeHtml(row.cost_center || '')}</td><td class="text-right">${formatMoney(row.amount, currency)}</td></tr>
            `).join('');
            const fiscalExpenseRows = (fiscalProfitAndLoss.expense_breakdown || []).map(row => `
                <tr><td>Expense</td><td>${escapeHtml(row.category || '')}</td><td>${escapeHtml(row.account)}</td><td>${escapeHtml(row.cost_center || '')}</td><td class="text-right">${formatMoney(row.amount, currency)}</td></tr>
            `).join('');
            const budgetRows = (budget.rows || []).map(row => `
                <tr>
                    <td>${escapeHtml(row.account)}</td><td>${escapeHtml(row.dimension || '')}</td>
                    <td class="text-right">${formatMoney(row.budget_amount, currency)}</td>
                    <td class="text-right">${formatMoney(row.actual_expense, currency)}</td>
                    <td class="text-right">${formatMoney(row.remaining, currency)}</td>
                    <td>${formatPercent(row.utilisation_rate)}</td>
                    <td><button class="btn btn-xs btn-default open-budget" data-name="${escapeHtml(row.budget)}">Open</button></td>
                </tr>
            `).join('');
            const payrollRows = (payroll.payroll_entries || []).map(entry => `
                <tr>
                    <td>${escapeHtml(entry.name)}</td><td>${escapeHtml(entry.payroll_frequency || '')}</td>
                    <td>${escapeHtml(entry.start_date || '')} – ${escapeHtml(entry.end_date || '')}</td>
                    <td>${escapeHtml(entry.status || (Number(entry.docstatus) === 1 ? 'Submitted' : 'Draft'))}</td>
                    <td><button class="btn btn-xs btn-default open-payroll-entry" data-name="${escapeHtml(entry.name)}">Open</button></td>
                </tr>
            `).join('');
            const fundRows = (fundRequests.items || []).map(request => `
                <tr>
                    <td>${escapeHtml(request.name)}</td><td>${escapeHtml(request.purpose)}</td><td>${escapeHtml(request.status)}</td>
                    <td class="text-right">${formatMoney(request.requested_amount, currency)}</td>
                    <td class="text-right">${formatMoney(request.disbursed_amount, currency)}</td>
                    <td>${formatPercent(request.progress)}</td>
                    <td><button class="btn btn-xs btn-default open-fund-request" data-name="${escapeHtml(request.name)}">Open</button></td>
                </tr>
            `).join('');

            operationsHtml = `
                <h4 style="margin-top:0;">Whole-School Financial Position</h4>
                <div class="text-muted" style="margin-bottom:16px;">
                    Term income is student fees collected from invoices assigned to <b>${escapeHtml(data.school_term.name)}</b>.
                    Expenses are submitted General Ledger entries for <b>${escapeHtml(operations.scope)}</b> from
                    ${escapeHtml(data.school_term.start_date)} through ${escapeHtml(operations.as_of)}.
                    Group Cost Centers include their descendants. Cash is the company-wide bank/cash balance.
                </div>
                ${diagnosticRows ? `<div class="alert alert-info"><b>Finance checks</b><ul style="margin-bottom:0;">${diagnosticRows}</ul></div>` : ''}
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:20px;">
                    <div class="card" style="padding:14px;"><b>Term income</b><div style="margin-top:8px;">Student fees collected: ${formatMoney(operations.student_fee_income, currency)}</div><div class="text-muted">Ledger-recognised income: ${formatMoney(operations.ledger_term_income, currency)}</div></div>
                    <div class="card" style="padding:14px;"><b>Expense composition</b><div style="margin-top:8px;">Wages: ${operations.wage_expense_account_configured ? formatMoney(operations.wage_expense, currency) : 'account not configured'}</div><div>Other expenses: ${formatMoney(operations.other_expenses, currency)}</div></div>
                    <div class="card" style="padding:14px;"><b>Budget (${escapeHtml(budget.fiscal_year || 'not set')})</b><div style="margin-top:8px;">${formatMoney(budget.used, currency)} used of ${formatMoney(budget.budget_total, currency)}</div><div>${formatMoney(budget.remaining, currency)} remaining (${formatPercent(budget.utilisation_rate)})</div><div class="text-muted">Fiscal-year actual through ${escapeHtml(operations.as_of)}</div></div>
                    <div class="card" style="padding:14px;"><b>Frappe HR payroll</b><div style="margin-top:8px;">${formatMoney(payroll.gross_pay, currency)} submitted gross pay</div><div>${formatMoney(payroll.net_pay, currency)} submitted net pay</div><div>${formatMoney(payroll.wage_gl_expense, currency)} posted wage expense</div><div>${payroll.payroll_payable_available ? `${formatMoney(payroll.payroll_payable, currency)} payable` : 'payable account not configured'}</div>${payroll.reconciliation_status === 'warning' ? `<div class="text-danger" style="margin-top:8px;"><b>Unreconciled:</b> ${escapeHtml(payroll.reconciliation_message || '')}</div>` : ''}</div>
                    <div class="card" style="padding:14px;"><b>Fiscal Year P&amp;L</b><div style="margin-top:8px;">Income: ${formatMoney(fiscalProfitAndLoss.income, currency)}</div><div>Expenses: ${formatMoney(fiscalProfitAndLoss.expenses, currency)}</div><div>Net result: ${formatMoney(fiscalProfitAndLoss.net_result, currency)}</div></div>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
                    <button class="btn btn-primary btn-sm new-fund-request">New Fund Request</button>
                    <button class="btn btn-default btn-sm open-budgets">Budgets</button>
                    <button class="btn btn-default btn-sm open-profit-loss">Profit and Loss</button>
                    <button class="btn btn-default btn-sm open-balance-sheet">Balance Sheet</button>
                    <button class="btn btn-default btn-sm open-cash-flow">Cash Flow</button>
                    <button class="btn btn-default btn-sm open-general-ledger">General Ledger</button>
                    <button class="btn btn-default btn-sm open-payables">Accounts Payable</button>
                    <button class="btn btn-default btn-sm open-finance-settings">Finance Settings</button>
                </div>
                <h5>Term Collected Fees and Expenses</h5>
                <div style="overflow-x:auto;margin-bottom:20px;"><table class="table table-bordered table-hover">
                    <thead><tr><th>Type</th><th>Category</th><th>Account</th><th>Cost Center</th><th>Amount</th></tr></thead>
                    <tbody>${incomeRows}${expenseRows}${(!incomeRows && !expenseRows) ? '<tr><td colspan="5">No collected fees or matching expense entries.</td></tr>' : ''}</tbody>
                    <tfoot>
                        <tr><th colspan="4">Term Income</th><th class="text-right">${formatMoney(operations.term_income, currency)}</th></tr>
                        <tr><th colspan="4">Term Expenses</th><th class="text-right">${formatMoney(operations.term_expenses, currency)}</th></tr>
                        <tr><th colspan="4">Operating Result</th><th class="text-right">${formatMoney(operations.operating_surplus, currency)}</th></tr>
                    </tfoot>
                </table></div>
                <h5>Fiscal Year Profit and Loss Detail</h5>
                <div class="text-muted" style="margin-bottom:8px;">${escapeHtml(fiscalProfitAndLoss.fiscal_year || 'Fiscal Year')}: ${escapeHtml(fiscalProfitAndLoss.start_date || '')} through ${escapeHtml(fiscalProfitAndLoss.end_date || operations.as_of || '')}. This is broader than the selected School Term.</div>
                <div style="overflow-x:auto;margin-bottom:20px;"><table class="table table-bordered table-hover">
                    <thead><tr><th>Type</th><th>Category</th><th>Account</th><th>Cost Center</th><th>Amount</th></tr></thead>
                    <tbody>${fiscalIncomeRows}${fiscalExpenseRows}${(!fiscalIncomeRows && !fiscalExpenseRows) ? '<tr><td colspan="5">No matching fiscal-year income or expense GL entries.</td></tr>' : ''}</tbody>
                    <tfoot>
                        <tr><th colspan="4">Fiscal Year Income</th><th class="text-right">${formatMoney(fiscalProfitAndLoss.income, currency)}</th></tr>
                        <tr><th colspan="4">Fiscal Year Expenses</th><th class="text-right">${formatMoney(fiscalProfitAndLoss.expenses, currency)}</th></tr>
                        <tr><th colspan="4">Fiscal Year Net Result</th><th class="text-right">${formatMoney(fiscalProfitAndLoss.net_result, currency)}</th></tr>
                    </tfoot>
                </table></div>
                <h5>Budget versus Actual</h5>
                <div style="overflow-x:auto;margin-bottom:20px;"><table class="table table-bordered table-hover">
                    <thead><tr><th>Account</th><th>Cost Center / Dimension</th><th>Budget</th><th>Actual</th><th>Remaining</th><th>Used</th><th>Action</th></tr></thead>
                    <tbody>${budgetRows || '<tr><td colspan="7">No submitted budget matches the company, fiscal year, and Cost Center scope.</td></tr>'}</tbody>
                </table></div>
                <h5>Frappe HR Payroll Entries</h5>
                ${payroll.scope_warning ? `<div class="alert alert-info">${escapeHtml(payroll.scope_warning)} The posted wage expense and salary budget are read from General Ledger Cost Centers, so they remain fully scoped.</div>` : ''}
                <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                    <button class="btn btn-default btn-sm open-payroll-entries">Payroll Entries</button>
                    <button class="btn btn-default btn-sm open-salary-slips">Salary Slips</button>
                    <button class="btn btn-default btn-sm open-salary-structures">Salary Structures</button>
                    <button class="btn btn-default btn-sm open-employees">Employees</button>
                </div>
                <div style="overflow-x:auto;margin-bottom:20px;"><table class="table table-bordered table-hover">
                    <thead><tr><th>Payroll Entry</th><th>Frequency</th><th>Period</th><th>Status</th><th>Action</th></tr></thead>
                    <tbody>${payrollRows || '<tr><td colspan="5">No Payroll Entry overlaps this School Term.</td></tr>'}</tbody>
                </table></div>
                <h5>Fund Request Progress</h5>
                <div style="overflow-x:auto;margin-bottom:20px;"><table class="table table-bordered table-hover">
                    <thead><tr><th>Request</th><th>Purpose</th><th>Status</th><th>Requested</th><th>Disbursed</th><th>Progress</th><th>Action</th></tr></thead>
                    <tbody>${fundRows || '<tr><td colspan="7">No fund requests for this School Term.</td></tr>'}</tbody>
                </table></div>
            `;
        }

        const ageingRows = (finance.ageing || [])
            .map(row => `
                <tr>
                    <td>${escapeHtml(row.bucket)}</td>
                    <td class="text-right">${formatMoney(row.amount, finance.currency)}</td>
                </tr>
            `)
            .join('');

        const batchRows = (finance.batches || [])
            .map(row => `
                <tr>
                    <td>${escapeHtml(row.student_batch)}</td>
                    <td>${formatNumber(row.student_count)}</td>
                    <td class="text-right">${formatMoney(row.invoiced, finance.currency)}</td>
                    <td class="text-right">${formatMoney(row.collected, finance.currency)}</td>
                    <td class="text-right">${formatMoney(row.outstanding, finance.currency)}</td>
                    <td>${formatPercent(row.collection_rate)}</td>
                </tr>
            `)
            .join('');

        const overdueRows = (finance.attention_items || [])
            .map(invoice => `
                <tr>
                    <td>${escapeHtml(invoice.student_name || invoice.student)}</td>
                    <td>${escapeHtml(invoice.name)}</td>
                    <td>${escapeHtml(invoice.due_date)}</td>
                    <td>${formatNumber(invoice.days_overdue)}</td>
                    <td class="text-right">${formatMoney(invoice.outstanding, finance.currency)}</td>
                    <td>
                        <button
                            class="btn btn-xs btn-default open-student-invoice"
                            data-name="${escapeHtml(invoice.name)}"
                        >Open</button>
                    </td>
                </tr>
            `)
            .join('');

        const studentFeesHtml = !finance.enabled
            ? '<div class="text-muted">Student fee invoice tracking is disabled in School MIS Settings.</div>'
            : !finance.available
                ? `<div class="alert alert-warning">${escapeHtml(finance.message || 'Student fee invoice information is unavailable.')}</div>`
                : `
            <hr>
            <h4>Student Fees, Invoices, and Collection</h4>
            <div class="text-muted" style="margin-bottom: 16px;">
                ${escapeHtml(finance.school_term || data.school_term.name)} student invoices,
                identified through ${escapeHtml(finance.scope_source || 'the education invoice link')}
                and scoped by ${escapeHtml(finance.term_scope || 'the School Term')}.
            </div>

            <div style="display: grid; grid-template-columns: minmax(260px, 1fr) minmax(420px, 2fr); gap: 18px; margin-bottom: 20px;">
                <div>
                    <h5>Outstanding Fee Ageing</h5>
                    <table class="table table-bordered">
                        <tbody>${ageingRows || '<tr><td>No outstanding balances</td></tr>'}</tbody>
                    </table>
                </div>
                <div style="overflow-x: auto;">
                    <h5>Collection by Student Batch</h5>
                    <table class="table table-bordered table-hover">
                        <thead>
                            <tr>
                                <th>Batch</th>
                                <th>Students</th>
                                <th>Invoiced</th>
                                <th>Collected</th>
                                <th>Outstanding</th>
                                <th>Rate</th>
                            </tr>
                        </thead>
                        <tbody>${batchRows || '<tr><td colspan="6">No batch information available.</td></tr>'}</tbody>
                    </table>
                </div>
            </div>

            <h5>Overdue Student Accounts Requiring Follow-up</h5>
            <div style="overflow-x: auto; margin-bottom: 14px;">
                <table class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th>Student</th>
                            <th>Invoice</th>
                            <th>Due Date</th>
                            <th>Days Overdue</th>
                            <th>Outstanding</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${overdueRows || '<tr><td colspan="6">No overdue student invoices.</td></tr>'}
                    </tbody>
                </table>
            </div>

            <button id="open-student-invoices-btn" class="btn btn-default btn-sm">
                Open Student Sales Invoices
            </button>
            <button id="email-overdue-fee-guardians-btn" class="btn btn-primary btn-sm" ${overdueRows ? '' : 'disabled'}>
                Email Guardians About Overdue Fees
            </button>
        `;

        container.html(operationsHtml + studentFeesHtml);

        setSectionVisibility('#finance-management-container', true);

        container
            .off('click', '.open-student-invoice')
            .on('click', '.open-student-invoice', function() {
                frappe.set_route('Form', 'Sales Invoice', $(this).data('name'));
            });

        $('#open-student-invoices-btn')
            .off('click')
            .on('click', function() {
                frappe.set_route('List', 'Sales Invoice');
            });

        $('#email-overdue-fee-guardians-btn').off('click').on('click', function() {
            showGuardianFeeReminderPreview(data.school_term.name, finance.currency);
        });

        container.off('click', '.open-finance-settings').on('click', '.open-finance-settings', () => frappe.set_route('Form', 'School MIS Settings'));
        container.off('click', '.new-fund-request').on('click', '.new-fund-request', () => frappe.new_doc('School Fund Request', {company: operations.company, cost_center: operations.cost_center}));
        container.off('click', '.open-fund-request').on('click', '.open-fund-request', function() { frappe.set_route('Form', 'School Fund Request', $(this).data('name')); });
        container.off('click', '.open-budget').on('click', '.open-budget', function() { frappe.set_route('Form', 'Budget', $(this).data('name')); });
        container.off('click', '.open-budgets').on('click', '.open-budgets', () => frappe.set_route('List', 'Budget'));
        container.off('click', '.open-profit-loss').on('click', '.open-profit-loss', () => frappe.set_route('query-report', 'Profit and Loss Statement'));
        container.off('click', '.open-balance-sheet').on('click', '.open-balance-sheet', () => frappe.set_route('query-report', 'Balance Sheet'));
        container.off('click', '.open-cash-flow').on('click', '.open-cash-flow', () => frappe.set_route('query-report', 'Cash Flow'));
        container.off('click', '.open-general-ledger').on('click', '.open-general-ledger', () => frappe.set_route('query-report', 'General Ledger'));
        container.off('click', '.open-payables').on('click', '.open-payables', () => frappe.set_route('query-report', 'Accounts Payable'));
        container.off('click', '.open-payroll-entry').on('click', '.open-payroll-entry', function() { frappe.set_route('Form', 'Payroll Entry', $(this).data('name')); });
        container.off('click', '.open-payroll-entries').on('click', '.open-payroll-entries', () => frappe.set_route('List', 'Payroll Entry'));
        container.off('click', '.open-salary-slips').on('click', '.open-salary-slips', () => frappe.set_route('List', 'Salary Slip'));
        container.off('click', '.open-salary-structures').on('click', '.open-salary-structures', () => frappe.set_route('List', 'Salary Structure'));
        container.off('click', '.open-employees').on('click', '.open-employees', () => frappe.set_route('List', 'Employee'));

    }


    function showGuardianFeeReminderPreview(schoolTerm, currency) {
        frappe.call({
            method: 'high_school.high_school.mis.actions.get_guardian_fee_reminder_preview',
            args: {school_term: schoolTerm},
            freeze: true,
            freeze_message: __('Resolving guardian accounts and email addresses...'),
            callback(r) {
                const preview = r.message || {};
                const recipients = preview.recipients || [];
                const rows = recipients.map(recipient => `
                    <tr>
                        <td><input type="checkbox" class="guardian-fee-recipient" data-email="${escapeHtml(recipient.email)}" checked></td>
                        <td>${escapeHtml(recipient.guardian_name)}</td>
                        <td>${escapeHtml(recipient.email)}</td>
                        <td>${escapeHtml((recipient.student_names || []).join(', '))}</td>
                        <td>${formatNumber(recipient.invoice_count)}</td>
                        <td class="text-right">${formatMoney(recipient.total_outstanding, preview.currency || currency)}</td>
                    </tr>
                `).join('');
                const dialog = new frappe.ui.Dialog({
                    title: __('Guardian Overdue Fee Reminders'),
                    size: 'extra-large',
                    fields: [{fieldname: 'preview', fieldtype: 'HTML'}],
                    primary_action_label: __('Queue Selected Emails'),
                    primary_action() {
                        const emails = dialog.$wrapper.find('.guardian-fee-recipient:checked')
                            .map(function() { return $(this).data('email'); }).get();
                        if (!emails.length) {
                            frappe.msgprint(__('Select at least one guardian.'));
                            return;
                        }
                        frappe.confirm(
                            __('Queue overdue-fee reminders for {0} guardian(s)?', [emails.length]),
                            () => frappe.call({
                                method: 'high_school.high_school.mis.actions.send_guardian_fee_reminders',
                                args: {school_term: schoolTerm, selected_emails: JSON.stringify(emails)},
                                freeze: true,
                                freeze_message: __('Queueing guardian fee reminders...'),
                                callback(sendResult) {
                                    if (sendResult.exc) return;
                                    dialog.hide();
                                    frappe.msgprint({
                                        title: __('Guardian Reminders Queued'),
                                        indicator: 'green',
                                        message: __('Queued overdue-fee reminders for {0} guardian(s).', [(sendResult.message || {}).recipient_count || 0])
                                    });
                                }
                            })
                        );
                    }
                });
                dialog.fields_dict.preview.$wrapper.html(`
                    <div class="text-muted" style="margin-bottom:12px;">
                        Email addresses come from enabled User accounts linked to each Guardian.
                        ${formatNumber(preview.invoices_without_guardian_email || 0)} overdue invoice(s) have no resolvable guardian User email and are excluded.
                    </div>
                    <div style="overflow-x:auto"><table class="table table-bordered table-hover">
                        <thead><tr><th>Send</th><th>Guardian</th><th>Email</th><th>Student(s)</th><th>Invoices</th><th>Outstanding</th></tr></thead>
                        <tbody>${rows || '<tr><td colspan="6">No guardian User email could be resolved for current overdue invoices.</td></tr>'}</tbody>
                    </table></div>
                `);
                if (!recipients.length) dialog.disable_primary_action();
                dialog.show();
            }
        });
    }


    // =========================================================
    // Insights
    // =========================================================

    function renderInsights(settings) {

        const dashboards = [
            ['#attendance-insights-card', '#insights-container', settings.attendance_insights_dashboard_url],
            ['#assessment-insights-card', '#assessment-insights-container', settings.assessment_insights_dashboard_url],
            ['#finance-insights-card', '#finance-insights-container', settings.finance_insights_dashboard_url]
        ];

        dashboards.forEach(([card, selector, url]) => {
            if (!url) {
                setSectionVisibility(card, false);
                return;
            }

            setSectionVisibility(card, true);
            $(selector).html(`
                <iframe
                    src="${escapeHtml(url)}"
                    title="School analytics dashboard"
                    loading="lazy"
                    style="width: 100%; height: 750px; border: none;"
                ></iframe>
            `);
        });

    }


    // =========================================================
    // Error
    // =========================================================

    function showError(message) {

        $('#attendance-kpis, #assessment-kpis, #finance-kpis')
            .html('');


        $('#executive-alerts')
            .html(`

                <div
                    class="alert alert-danger"
                >
                    ${escapeHtml(
                        message
                    )}
                </div>

            `);

    }

};
