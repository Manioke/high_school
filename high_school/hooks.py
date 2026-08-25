app_name = "high_school"
app_title = "High School"
app_publisher = "Sione Hikaione Fonua Kata"
app_description = "A custom app that extends the functionality of the education app so that you can easily change the School settings for different high schools and enables different modules or fields like is board school and other settings spefic to each school will only show if you set it in the settings"
app_email = "johnnyhikaione@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["education"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "high_school",
# 		"logo": "/assets/high_school/logo.png",
# 		"title": "High School",
# 		"route": "/high_school",
# 		"has_permission": "high_school.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------
import high_school.high_school.api
from high_school.high_school.patches import apply_patches

# include js, css files in header of desk.html
# app_include_css = "/assets/high_school/css/high_school.css"
# app_include_js = "/assets/high_school/js/high_school.js"

# include js, css files in header of web template
# web_include_css = "/assets/high_school/css/high_school.css"
# web_include_js = "/assets/high_school/js/high_school.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "high_school/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
doctype_list_js = {
    "Course Schedule": "public/js/course_schedule_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}
doctype_js = {
    "Student Group": "public/js/student_group_custom.js",
    "Assessment Plan": "public/js/assessment_plan.js",
    "Course Scheduling Tool": "public/js/course_scheduling_tool_extension.js",
    "Student Leave Application": "public/js/student_leave_application.js",
    "Program Enrollment": "public/js/program_enrollment.js",
    "Student Applicant": "public/js/student_applicant.js",
    "Program Enrollment Tool": "public/js/program_enrollment_tool_override.js"
}

doctype_calendar_js = {
    "Exam Paper Requirement": "public/js/exam_paper_requirement_calendar.js",
    "Assessment Plan": "public/js/assessment_plan_calendar.js"
}
# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "high_school/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "high_school.utils.jinja_methods",
# 	"filters": "high_school.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "high_school.install.before_install"
# after_install = "high_school.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "high_school.uninstall.before_uninstall"
# after_uninstall = "high_school.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "high_school.utils.before_app_install"
# after_app_install = "high_school.utils.after_app_install"


after_migrate = [
    "high_school.high_school.student_utils.create_education_settings_custom_fields"
]

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "high_school.utils.before_app_uninstall"
# after_app_uninstall = "high_school.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "high_school.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
    "Exam Paper Requirement": "high_school.high_school.exam_preparation.get_requirement_permission_query_conditions",
    "Course Schedule": "high_school.api.permissions.course_schedule_query",
    "Student Attendance": "high_school.api.permissions.student_attendance_query",
    "Assessment Plan": "high_school.api.permissions.assessment_plan_query",
    "Assessment Result": "high_school.api.permissions.assessment_result_query",
}

has_permission = {
    "Exam Paper Requirement": "high_school.high_school.exam_preparation.has_requirement_permission",
    "Course Schedule": "high_school.api.permissions.course_schedule_has_permission",
    "Student Attendance": "high_school.api.permissions.student_attendance_has_permission",
    "Assessment Plan": "high_school.api.permissions.assessment_plan_has_permission",
    "Assessment Result": "high_school.api.permissions.assessment_result_has_permission",
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

#override_doctype_class = {
#    "Student Leave Application": "high_school.high_school.api.HighSchoolLeaveApplication"
#}

# Document Events
# ---------------
# Hook on document methods and events
# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"Assessment Plan": {
		"on_update": "high_school.high_school.exam_preparation.refresh_requirements_for_assessment_plan",
		"on_cancel": "high_school.high_school.exam_preparation.refresh_requirements_for_assessment_plan",
		"after_delete": "high_school.high_school.exam_preparation.refresh_requirements_for_assessment_plan",
	},
    "Student Leave Application": {
        "on_submit": "high_school.high_school.attendance_utils.update_attendance_on_leave_approval"
    },
    "Student Attendance": {
        "validate": [
            "high_school.high_school.attendance_utils.process_standard_attendance_punishment",
            "high_school.api.permissions.validate_student_attendance"
        ],
        "on_submit": "high_school.high_school.attendance_utils.trigger_standard_attendance_recalc",
        "on_cancel": "high_school.high_school.attendance_utils.trigger_standard_attendance_recalc",
    },
    "Assessment Result": {
        "validate":
            "high_school.api.permissions.validate_assessment_result",
    },
    "Taliui Akonofo": {
        "on_submit": "high_school.high_school.attendance_utils.trigger_standard_attendance_recalc",
        "on_cancel": "high_school.high_school.attendance_utils.trigger_standard_attendance_recalc",
    },
    "Program Enrollment": {
        "on_submit": [
            "high_school.high_school.fee_utils.generate_custom_fees",
            "high_school.high_school.student_utils.update_student_fields"
        ]
    }
}
#doc_events = {
#    "Student Leave Application": {
#        "on_submit": "high_school.high_school.api.create_course_leave_attendance"
#    }
#}

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"high_school.tasks.all"
# 	],
	"daily": [
		"high_school.high_school.exam_preparation.send_exam_preparation_reminders"
	],
# 	"hourly": [
# 		"high_school.tasks.hourly"
# 	],
# 	"weekly": [
# 		"high_school.tasks.weekly"
# 	],
# 	"monthly": [
# 		"high_school.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "high_school.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "high_school.event.get_events"
# }
#

override_whitelisted_methods = {
    "education.education.doctype.student_group.student_group.get_students": "high_school.high_school.api.get_students_custom",
    "education.education.api.mark_attendance": "high_school.high_school.api.custom_mark_attendance",
    "education.education.api.get_course_schedule_events": "high_school.high_school.api.get_course_schedule_events",
    "education.education.api.get_assessment_students": "high_school.high_school.api.get_assessment_students",
    "education.education.api.mark_assessment_result": "high_school.high_school.api.mark_assessment_result",
    "education.education.api.submit_assessment_results": "high_school.high_school.api.submit_assessment_results",
#    "education.education.api.get_student_invoices": "high_school.high_school.api.get_student_invoices"
}
# Replace the Core Class with your Smart Class

#override_doctype_class = {
#    "Student Leave Application": "high_school.high_school.api.HighSchoolLeaveApplication"
#}

# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "high_school.task.get_dashboard_data"
# }

# JS injection for Education App DocTypes
# ---------------

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["high_school.utils.before_request"]
# after_request = ["high_school.utils.after_request"]

# Job Events
# ----------
# before_job = ["high_school.utils.before_job"]
# after_job = ["high_school.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"high_school.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }
#on_login = "high_school.high_school.auth.after_login"
on_session_creation = [
    "high_school.high_school.auth.redirect_after_login"
]
# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["module", "=", "High School"]
        ]
    },
    {
        "dt": "Client Script",
        "filters": [
            ["module", "=", "High School"]
        ]
    },
    {
        "dt": "Custom DocPerm",
        "filters": [
            [
                "parent", 
                "in", 
                [
                    # Instructor Roles Added Permissions
                    "Course Schedule", 
                    "Assessment Criteria", 
                    "Assessment Plan", 
                    "Assessment Result",
                    
                    # Education Manager Roles Added Permissions
                    "Academic Year", 
                    "School Term", 
                    "Assessment Group", 
                    "Student Batch Name", 
                    "Grading Scale", 
                    "Room",
                    
                    # Keeping your prior Sales Invoice custom rules active
                    "Sales Invoice"
                ]
            ]
        ]
    }
]