//frappe.pages['executive-dashboard'].on_page_load = function(wrapper) {
//	var page = frappe.ui.make_app_page({
//		parent: wrapper,
//		title: 'Executive MIS Dashboard',
//		single_column: true
//	});
//}


frappe.pages['executive-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'School Executive Dashboard',
        single_column: true
    });

    // Render the layout HTML
    $(page.body).html(`
        <div class="executive-dashboard-container" style="padding: 15px;">
            <!-- Commentary / Summary Section -->
            <div class="card" style="padding: 15px; margin-bottom: 20px; background-color: #f8f9fa; border-left: 4px solid #007bff;">
                <h4 style="margin-top: 0;">📋 Daily Executive Briefing</h4>
                <div id="ai-summary-content"><i>Loading insights commentary...</i></div>
            </div>

            <!-- Embedded Interactive Frappe Insights Dashboard -->
            <div class="card" style="padding: 10px;">
                <iframe src="/insights/dashboards/public/<YOUR-INSIGHTS-DASHBOARD-ID>" 
                        style="width: 100%; height: 750px; border: none;"></iframe>
            </div>
        </div>
    `);

    // Fetch dynamic commentary from Python API in high_school app
    frappe.call({
        method: 'high_school.high_school.api.get_executive_summary',
        callback: function(r) {
            if (r.message) {
                $('#ai-summary-content').html(r.message.summary_html);
            }
        }
    });
};