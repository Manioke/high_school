// Copyright (c) 2026, Sione Hikaione Fonua Kata and contributors
// For license information, please see license.txt

// frappe.ui.form.on("MIS Issue", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on(
    'MIS Issue',
    {

        refresh(frm) {

            if (frm.is_new()) {
                return;
            }


            // =============================================
            // View source document
            // =============================================

            if (
                frm.doc.reference_doctype
                &&
                frm.doc.reference_name
            ) {

                frm.add_custom_button(
                    __('View Source'),
                    function() {

                        frappe.set_route(
                            'Form',
                            frm.doc.reference_doctype,
                            frm.doc.reference_name
                        );

                    }
                );

            }


            // =============================================
            // Open / Under Review
            // =============================================

            if (
                frm.doc.status === 'Open'
            ) {

                frm.add_custom_button(
                    __('Mark Under Review'),
                    function() {

                        frappe.call({

                            method:
                                'high_school.high_school.management_mis.mark_issue_under_review',

                            args: {
                                issue_name:
                                    frm.doc.name
                            },

                            callback() {

                                frm.reload_doc();

                            }

                        });

                    },
                    __('Actions')
                );

            }


            // =============================================
            // Resolve
            // =============================================

            if (
                frm.doc.status === 'Open'
                ||
                frm.doc.status === 'Under Review'
            ) {

                frm.add_custom_button(
                    __('Resolve Issue'),
                    function() {

                        show_resolution_dialog(
                            frm
                        );

                    },
                    __('Actions')
                );

            }


            // =============================================
            // Reopen
            // =============================================

            if (
                frm.doc.status === 'Resolved'
                ||
                frm.doc.status === 'Dismissed'
            ) {

                frm.add_custom_button(
                    __('Reopen Issue'),
                    function() {

                        frappe.confirm(
                            __(
                                'Reopen this management issue?'
                            ),

                            function() {

                                frappe.call({

                                    method:
                                        'high_school.high_school.management_mis.reopen_issue',

                                    args: {
                                        issue_name:
                                            frm.doc.name
                                    },

                                    callback() {

                                        frm.reload_doc();

                                    }

                                });

                            }
                        );

                    },
                    __('Actions')
                );

            }

        }

    }
);


function show_resolution_dialog(frm) {

    const dialog =
        new frappe.ui.Dialog({

            title:
                __('Resolve MIS Issue'),

            fields: [

                {
                    fieldname:
                        'resolution_type',

                    label:
                        __('Resolution Type'),

                    fieldtype:
                        'Select',

                    reqd:
                        1,

                    options: [
                        'Class Cancelled',
                        'School Event',
                        'Timetable Change',
                        'Teacher Absent',
                        'Attendance Not Recoverable',
                        'Administrative Error',
                        'Issue No Longer Applicable',
                        'Other'
                    ].join('\n')
                },

                {
                    fieldname:
                        'resolution_notes',

                    label:
                        __('Resolution Notes'),

                    fieldtype:
                        'Small Text',

                    reqd:
                        1
                },

                {
                    fieldname:
                        'exclude_from_kpis',

                    label:
                        __(
                            'Exclude from KPI Calculations'
                        ),

                    fieldtype:
                        'Check',

                    default:
                        0,

                    description:
                        __(
                            'Use this only when the event '
                            + 'should not have counted as an '
                            + 'expected activity, for example '
                            + 'a cancelled class.'
                        )
                }

            ],

            primary_action_label:
                __('Resolve Issue'),

            primary_action(values) {

                frappe.call({

                    method:
                        'high_school.high_school.management_mis.resolve_issue',

                    args: {
                        issue_name:
                            frm.doc.name,

                        resolution_type:
                            values.resolution_type,

                        resolution_notes:
                            values.resolution_notes,

                        exclude_from_kpis:
                            values.exclude_from_kpis
                    },

                    callback() {

                        dialog.hide();

                        frm.reload_doc();

                    }

                });

            }

        });


    dialog.show();

}