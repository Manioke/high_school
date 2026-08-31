frappe.pages['executive-dashboard'].on_page_load = function(wrapper) {

    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'School Executive Dashboard',
        single_column: true
    });


    // =========================================================
    // Configuration
    // =========================================================

    const INSIGHTS_DASHBOARD_URL = '';


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


            <!-- ============================================= -->
            <!-- KPIs -->
            <!-- ============================================= -->

            <div
                id="executive-kpis"
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
                    Executive Attention
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


            <!-- ============================================= -->
            <!-- Insights -->
            <!-- ============================================= -->

            <div
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

        </div>

    `);


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


            terms.forEach(term => {

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


            const selectedTerm =
                currentTerm
                || terms[0];


            selector.val(
                selectedTerm.name
            );


            updateTermDates(
                selectedTerm
            );


            loadExecutiveSummary(
                selectedTerm.name
            );


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

        $('#executive-kpis')
            .html(`

                <div
                    class="card"
                    style="padding: 20px;"
                >
                    Loading...
                </div>

            `);


        $('#executive-alerts')
            .html(`

                <i>
                    Loading management information...
                </i>

            `);


        $('#attendance-management-container')
            .hide();


        $('#student-management-container')
            .hide();


        $('#academic-operations-container')
            .hide();


        $('#academic-performance-container')
            .hide();


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

        renderInsights();

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
                    'Students requiring review',

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


        // -----------------------------------------------------
        // Assessment Operations
        // -----------------------------------------------------

        cards.push(
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


        cards.push(
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


        cards.push(
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


        cards.push(
            createKpiCard({

                title:
                    'School Average',

                value:
                    formatPercent(
                        performanceSummary.school_average
                    ),

                subtitle:
                    `${formatNumber(performanceSummary.students_analysed)} student(s) analysed`,

                status:
                    performanceSummary.status || 'no_data'

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


        $('#executive-kpis')
            .html(
                cards.join('')
            );

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
                    No configured MIS alert rules
                    are currently triggered.
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

            $('#attendance-management-container')
                .hide();

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

            $('#attendance-management-container')
                .hide();

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

                </div>

            `);


        $('#attendance-management-container')
            .show();


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

                    <tr>

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

                        <tr>

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


        if (count <= 0) {

            $('#student-management-container')
                .hide();

            return;

        }


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
                            Persistent absence
                            requires review
                        </div>


                        <div
                            style="
                                color: #6c757d;
                            "
                        >

                            ${count}
                            student(s) currently exceed
                            the school's configured
                            persistent absence threshold.

                        </div>

                    </div>


                    <button
                        id="investigate-students-btn"
                        class="btn btn-primary btn-sm"
                    >
                        Investigate Students
                    </button>

                </div>

            `);


        $('#student-management-container')
            .show();


        $('#investigate-students-btn')
            .off('click')
            .on(
                'click',
                function() {

                    showStudentInvestigation(
                        persistent
                    );

                }
            );

    }


    // =========================================================
    // Student Investigation Dialog
    // =========================================================

    function showStudentInvestigation(
        persistent
    ) {

        const records = [];


        for (
            const mode
            of ['daily', 'course']
        ) {

            const modeData =
                persistent[mode] || {};


            if (!modeData.enabled) {
                continue;
            }


            for (
                const student
                of (
                    modeData
                        .flagged_students
                    || []
                )
            ) {

                records.push({
                    ...student,
                    attendance_type:
                        mode
                });

            }

        }


        const rows =
            records

                .map(student => `

                    <tr>

                        <td>
                            ${escapeHtml(
                                student.student_name
                                || student.student
                            )}
                        </td>

                        <td>
                            ${escapeHtml(
                                student.attendance_type
                            )}
                        </td>

                        <td>
                            ${student.present}
                        </td>

                        <td>
                            ${student.absent}
                        </td>

                        <td>
                            ${student.leave}
                        </td>

                        <td>
                            ${student.counted_records}
                        </td>

                        <td>
                            ${formatPercent(
                                student.absence_rate
                            )}
                        </td>

                        <td>
                            ${formatPercent(
                                student.threshold
                            )}
                        </td>

                    </tr>

                `)

                .join('');


        const dialog =
            new frappe.ui.Dialog({

                title:
                    'Persistent Absence Investigation',

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
                    Only students meeting the configured
                    minimum attendance-record requirement
                    and persistent absence threshold are
                    shown.
                </div>


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
                                <th>Student</th>
                                <th>Attendance Type</th>
                                <th>Present</th>
                                <th>Absent</th>
                                <th>Leave</th>
                                <th>Counted</th>
                                <th>Absence Rate</th>
                                <th>Threshold</th>
                            </tr>

                        </thead>


                        <tbody>

                            ${
                                rows
                                ||

                                `
                                    <tr>
                                        <td colspan="8">
                                            No students currently
                                            require investigation.
                                        </td>
                                    </tr>
                                `
                            }

                        </tbody>

                    </table>

                </div>

            `);


        dialog.show();

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

                <button
                    id="open-exam-coverage-report-btn"
                    class="btn btn-default btn-sm"
                >
                    Exam Preparation Coverage
                </button>

                <button
                    id="open-result-coverage-report-btn"
                    class="btn btn-default btn-sm"
                >
                    Result Submission Coverage
                </button>

            </div>

        `);

        $('#academic-operations-container').show();

        $('#review-academic-attention-btn')
            .off('click')
            .on('click', function() {
                showAcademicAttentionDialog(academics);
            });

        $('#open-exam-coverage-report-btn')
            .off('click')
            .on('click', function() {
                frappe.set_route(
                    'query-report',
                    'Exam Preparation Coverage'
                );
            });

        $('#open-result-coverage-report-btn')
            .off('click')
            .on('click', function() {
                frappe.set_route(
                    'query-report',
                    'Assessment Result Submission Coverage',
                    {school_term: data.school_term.name}
                );
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

        if (!performance.available) {

            $('#academic-performance-content').html(`
                <div style="color: #6c757d; margin-bottom: 14px;">
                    No School Performance Period has been configured
                    for this term yet.
                </div>
                <button
                    id="setup-performance-periods-btn"
                    class="btn btn-primary btn-sm"
                >
                    Set Up Performance Periods
                </button>
            `);

            $('#academic-performance-container').show();

            $('#setup-performance-periods-btn')
                .off('click')
                .on('click', function() {
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

        $('#academic-performance-content').html(`

            ${configurationWarning}

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

        `);

        $('#academic-performance-container').show();

        $('#open-performance-periods-btn')
            .off('click')
            .on('click', function() {
                frappe.set_route(
                    'List',
                    'School Performance Period',
                    {school_term: data.school_term.name}
                );
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
    // Insights
    // =========================================================

    function renderInsights() {

        if (!INSIGHTS_DASHBOARD_URL) {

            $('#insights-container')
                .html(`

                    <div
                        style="
                            padding: 20px;
                            color: #6c757d;
                        "
                    >
                        Insights dashboard URL
                        has not been configured.
                    </div>

                `);

            return;

        }


        $('#insights-container')
            .html(`

                <iframe
                    src="${escapeHtml(
                        INSIGHTS_DASHBOARD_URL
                    )}"
                    style="
                        width: 100%;
                        height: 750px;
                        border: none;
                    "
                >
                </iframe>

            `);

    }


    // =========================================================
    // Error
    // =========================================================

    function showError(message) {

        $('#executive-kpis')
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
