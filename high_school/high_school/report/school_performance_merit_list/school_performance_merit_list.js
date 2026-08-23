frappe.query_reports["School Performance Merit List"] = {
	filters: [
		{
			fieldname: "performance_period",
			label: __("Performance Period"),
			fieldtype: "Link",
			options: "School Performance Period",
			reqd: 1,
		},
		{
			fieldname: "top_n",
			label: __("Show Top"),
			fieldtype: "Int",
			default: 10,
		},
		{
			fieldname: "include_incomplete",
			label: __("Include Incomplete"),
			fieldtype: "Check",
			default: 0,
		},
	],
};
