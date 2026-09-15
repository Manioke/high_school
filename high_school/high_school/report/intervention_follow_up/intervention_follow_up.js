frappe.query_reports['Intervention Follow-up'] = {
    filters: [
        {fieldname: 'school_term', label: __('School Term'), fieldtype: 'Link', options: 'School Term'},
        {fieldname: 'intervention_type', label: __('Type'), fieldtype: 'Select', options: '\nAcademic\nAttendance'},
        {fieldname: 'assigned_to', label: __('Plan Owner'), fieldtype: 'Link', options: 'User'},
        {fieldname: 'attention_only', label: __('Only Recording / Follow-up Gaps'), fieldtype: 'Check', default: 1},
        {fieldname: 'include_closed', label: __('Include Closed Plans'), fieldtype: 'Check', default: 0},
    ],
};
