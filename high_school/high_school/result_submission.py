from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_days, getdate


MANAGER_ROLES = {"System Manager", "Education Manager"}


def _doctype_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _is_manager(user=None):
	return bool(set(frappe.get_roles(user)) & MANAGER_ROLES)


def _instructor_user(instructor):
	if not instructor:
		return None
	fields = _doctype_fields("Instructor")
	for fieldname in ("user", "user_id"):
		if fieldname in fields:
			user = frappe.db.get_value("Instructor", instructor, fieldname)
			if user:
				return user
	if "employee" in fields:
		employee = frappe.db.get_value("Instructor", instructor, "employee")
		if employee:
			return frappe.db.get_value("Employee", employee, "user_id")
	return None


def resolve_plan_responsibility(plan):
	if not frappe.db.exists("DocType", "Course Schedule"):
		return {"instructor": None, "responsible_user": None, "issue": _("Course Schedule is unavailable.")}
	fields = _doctype_fields("Course Schedule")
	if not {"student_group", "course", "instructor"}.issubset(fields):
		return {
			"instructor": None,
			"responsible_user": None,
			"issue": _("Course Schedule does not expose Student Group, Course, and Instructor."),
		}
	filters = {
		"student_group": plan.get("student_group"),
		"course": plan.get("course"),
		"docstatus": ["<", 2],
	}
	if "academic_year" in fields and plan.get("academic_year"):
		filters["academic_year"] = plan.get("academic_year")
	instructors = sorted(
		set(
			frappe.get_all(
				"Course Schedule",
				filters=filters,
				pluck="instructor",
			)
		)
		- {None, ""}
	)
	if not instructors:
		return {
			"instructor": None,
			"responsible_user": None,
			"issue": _("No scheduled Instructor was found for this Course and Student Group."),
		}
	if len(instructors) > 1:
		return {
			"instructor": None,
			"responsible_user": None,
			"issue": _("Different Course Schedules assign more than one Instructor: {0}.").format(
				", ".join(instructors)
			),
		}
	instructor = instructors[0]
	user = _instructor_user(instructor)
	if not user:
		return {
			"instructor": instructor,
			"responsible_user": None,
			"issue": _("Instructor {0} is not linked through Employee to a User account.").format(instructor),
		}
	return {"instructor": instructor, "responsible_user": user, "issue": None}


def calculate_result_due_date(cycle, plan):
	basis = cycle.result_deadline_basis or "After Cycle End Date"
	if basis == "Fixed Date":
		return cycle.fixed_result_deadline
	base_date = cycle.exam_end_date
	if basis == "After Assessment Date":
		base_date = plan.get("schedule_date") or cycle.exam_end_date
	return add_days(getdate(base_date), cycle.result_turnaround_days or 0) if base_date else None


def _requirement_for_plan(plan):
	filters = {
		"academic_year": plan.get("academic_year"),
		"assessment_group": plan.get("assessment_group"),
		"course": plan.get("course"),
		"status": ["in", ["Approved", "Plans Partially Created", "Complete"]],
	}
	candidates = frappe.get_all("Exam Paper Requirement", filters=filters, pluck="name")
	matches = []
	for name in candidates:
		if frappe.db.exists(
			"Exam Paper Affected Group",
			{
				"parent": name,
				"parenttype": "Exam Paper Requirement",
				"student_group": plan.get("student_group"),
			},
		):
			matches.append(name)
	return matches[0] if len(matches) == 1 else None


def sync_tracker_for_assessment_plan(doc, method=None, exam_paper_requirement=None):
	if not doc or not doc.get("name"):
		return None
	requirement = exam_paper_requirement or _requirement_for_plan(doc)
	name = frappe.db.get_value(
		"Assessment Result Submission Tracker", {"assessment_plan": doc.name}
	)
	if not requirement and not name:
		return None
	tracker = (
		frappe.get_doc("Assessment Result Submission Tracker", name)
		if name
		else frappe.new_doc("Assessment Result Submission Tracker")
	)
	tracker.assessment_plan = doc.name
	if requirement:
		tracker.exam_paper_requirement = requirement
	if tracker.is_new():
		tracker.insert(ignore_permissions=True)
	else:
		tracker.save(ignore_permissions=True)
	return tracker.name


def sync_tracker_for_assessment_result(doc, method=None):
	if not doc or not doc.get("assessment_plan"):
		return
	name = frappe.db.get_value(
		"Assessment Result Submission Tracker", {"assessment_plan": doc.assessment_plan}
	)
	if not name:
		plan = frappe.get_doc("Assessment Plan", doc.assessment_plan)
		name = sync_tracker_for_assessment_plan(plan)
	if name:
		tracker = frappe.get_doc("Assessment Result Submission Tracker", name)
		tracker.save(ignore_permissions=True)


def validate_assessment_result_responsibility(doc, method=None):
	"""Stop one instructor from entering results for another scheduled teacher."""
	if not doc or not doc.get("assessment_plan"):
		return
	user = frappe.session.user
	if user in {"Administrator", "Guest"} or _is_manager(user):
		return
	tracker = frappe.db.get_value(
		"Assessment Result Submission Tracker",
		{"assessment_plan": doc.assessment_plan},
		["responsible_user", "instructor_mapping_issue"],
		as_dict=True,
	)
	if not tracker:
		return
	if tracker.instructor_mapping_issue:
		frappe.throw(
			_("Results cannot be entered until the Course Schedule instructor mapping is corrected: {0}").format(
				tracker.instructor_mapping_issue
			),
			frappe.PermissionError,
		)
	if tracker.responsible_user != user:
		frappe.throw(
			_("Only the instructor scheduled for this Course and Student Group can enter these Assessment Results."),
			frappe.PermissionError,
		)


def generate_trackers_for_cycle(examination_cycle):
	requirements = frappe.get_all(
		"Exam Paper Requirement",
		filters={"examination_cycle": examination_cycle},
		pluck="name",
	)
	created = updated = skipped = mapping_issues = 0
	for requirement_name in requirements:
		requirement = frappe.get_doc("Exam Paper Requirement", requirement_name)
		for affected in requirement.affected_student_groups:
			plan_name = affected.assessment_plan or frappe.db.get_value(
				"Assessment Plan",
				{
					"academic_year": requirement.academic_year,
					"assessment_group": requirement.assessment_group,
					"course": requirement.course,
					"student_group": affected.student_group,
					"docstatus": ["<", 2],
				},
			)
			if not plan_name:
				skipped += 1
				continue
			existing = frappe.db.get_value(
				"Assessment Result Submission Tracker", {"assessment_plan": plan_name}
			)
			plan = frappe.get_doc("Assessment Plan", plan_name)
			tracker_name = sync_tracker_for_assessment_plan(
				plan, exam_paper_requirement=requirement.name
			)
			tracker = frappe.get_doc("Assessment Result Submission Tracker", tracker_name)
			created += int(not existing)
			updated += int(bool(existing))
			mapping_issues += int(bool(tracker.instructor_mapping_issue))
	return {
		"created": created,
		"updated": updated,
		"skipped": skipped,
		"mapping_issues": mapping_issues,
	}


def refresh_open_result_trackers():
	for name in frappe.get_all(
		"Assessment Result Submission Tracker",
		filters={"status": ["not in", ["Results Complete", "Plan Cancelled"]]},
		pluck="name",
	):
		try:
			frappe.get_doc("Assessment Result Submission Tracker", name).save(ignore_permissions=True)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Result submission tracker refresh failed")


def get_tracker_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if not user or user == "Administrator" or _is_manager(user):
		return ""
	escaped = frappe.db.escape(user)
	return """(
		`tabAssessment Result Submission Tracker`.`responsible_user` = {user}
		or `tabAssessment Result Submission Tracker`.`hod_user` = {user}
	)""".format(user=escaped)


def has_tracker_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator" or _is_manager(user):
		return True
	if user not in {doc.responsible_user, doc.hod_user}:
		return False
	if permission_type in {"create", "delete", "submit", "cancel", "amend"}:
		return False
	return True


def get_performance_readiness(period):
	from high_school.high_school.performance import (
		_get_all_student_groups,
		_get_assessment_plans,
		_get_group_students,
	)

	student_rows = _get_group_students(period.main_student_group)
	students = [row.student for row in student_rows]
	groups_by_student = _get_all_student_groups(students, period.academic_year)
	all_groups = set().union(*groups_by_student.values()) if groups_by_student else set()
	components = [row.assessment_group for row in period.components]
	plans = _get_assessment_plans(all_groups, components, period.academic_year)
	issues = []

	if not plans:
		issues.append({"type": "No Assessment Plans", "message": _("No relevant Assessment Plans were found.")})

	plan_keys = {(plan.student_group, plan.course, plan.assessment_group) for plan in plans}
	for student in students:
		student_plans = [plan for plan in plans if plan.student_group in groups_by_student.get(student, set())]
		courses = {plan.course for plan in student_plans}
		for course in courses:
			for component in components:
				if not any(
					(group, course, component) in plan_keys
					for group in groups_by_student.get(student, set())
				):
					issues.append(
						{
							"type": "Missing Assessment Plan",
							"student": student,
							"course": course,
							"assessment_group": component,
							"message": _("Missing Assessment Plan for {0}, {1}, {2}.").format(
								student, course, component
							),
						}
					)

	for plan in plans:
		applicable_students = {
			student for student in students if plan.student_group in groups_by_student.get(student, set())
		}
		if not applicable_students:
			continue
		tracker_name = frappe.db.get_value(
			"Assessment Result Submission Tracker", {"assessment_plan": plan.name}
		)
		if not tracker_name:
			issues.append(
				{
					"type": "Missing Result Tracker",
					"assessment_plan": plan.name,
					"course": plan.course,
					"message": _("Assessment Plan {0} has no result-submission tracker.").format(plan.name),
				}
			)
			continue
		tracker = frappe.db.get_value(
			"Assessment Result Submission Tracker",
			tracker_name,
			["status", "responsible_user", "instructor_mapping_issue"],
			as_dict=True,
		)
		if tracker.instructor_mapping_issue:
			issues.append(
				{
					"type": "Instructor Mapping Error",
					"assessment_plan": plan.name,
					"course": plan.course,
					"message": tracker.instructor_mapping_issue,
				}
			)
		candidate_rows = frappe.get_all(
			"Assessment Result Submission Candidate",
			filters={
				"parent": tracker_name,
				"parenttype": "Assessment Result Submission Tracker",
				"student": ["in", list(applicable_students)],
				"result_status": ["in", ["Pending", "Draft"]],
			},
			fields=["student", "student_name", "result_status"],
		)
		for candidate in candidate_rows:
			issues.append(
				{
					"type": "Unresolved Result",
					"assessment_plan": plan.name,
					"course": plan.course,
					"student": candidate.student,
					"responsible_user": tracker.responsible_user,
					"message": _("{0} has a {1} result for {2}.").format(
						candidate.student_name or candidate.student,
						candidate.result_status.lower(),
						plan.course,
					),
				}
			)

	return {
		"ready": not issues,
		"issue_count": len(issues),
		"issues": issues,
		"plans_checked": len(plans),
		"students_checked": len(students),
	}


@frappe.whitelist()
def check_performance_readiness(performance_period):
	period = frappe.get_doc("School Performance Period", performance_period)
	period.check_permission("read")
	return get_performance_readiness(period)
