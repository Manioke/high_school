from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt


def _as_list(value):
	if not value:
		return []
	if isinstance(value, str):
		return json.loads(value)
	return value


def _meta_fields(doctype):
	return {field.fieldname: field for field in frappe.get_meta(doctype).fields}


def _available_field(fields, *names):
	return next((name for name in names if name in fields), None)


def _group_filters(academic_year, program=None, student_batch=None):
	fields = _meta_fields("Student Group")
	filters = {"academic_year": academic_year}
	if "disabled" in fields:
		filters["disabled"] = 0
	if program and "program" in fields:
		filters["program"] = program
	batch_field = _available_field(fields, "student_batch", "student_batch_name", "batch")
	if student_batch and batch_field:
		filters[batch_field] = student_batch
	return filters


def _course_schedule_candidates(group_names, academic_year, course):
	if not group_names or not frappe.db.exists("DocType", "Course Schedule"):
		return []

	fields = _meta_fields("Course Schedule")
	if "student_group" not in fields or "course" not in fields:
		return []

	query_fields = ["student_group", "course"]
	for fieldname in ("instructor", "room"):
		if fieldname in fields:
			query_fields.append(fieldname)

	filters = {
		"student_group": ["in", group_names],
		"course": course,
		"docstatus": ["<", 2],
	}
	if "academic_year" in fields:
		filters["academic_year"] = academic_year

	return frappe.get_all(
		"Course Schedule",
		filters=filters,
		fields=query_fields,
		order_by="student_group asc, course asc",
	)


def _group_course_candidates(groups, course):
	rows = []
	for group in groups:
		if group.get("course") == course:
			rows.append(
				frappe._dict(
					student_group=group.name,
					course=group.course,
					instructor=None,
					room=None,
				)
			)
	return rows


def _deduplicate_candidates(rows):
	by_key = {}
	for row in rows:
		student_group = row.get("student_group")
		course = row.get("course")
		if not student_group or not course:
			continue
		key = (student_group, course)
		current = by_key.get(key)
		if not current:
			by_key[key] = {
				"student_group": student_group,
				"course": course,
				"instructor": row.get("instructor"),
				"room": row.get("room"),
				"instructors": {row.get("instructor")} if row.get("instructor") else set(),
			}
		else:
			if row.get("instructor"):
				current["instructors"].add(row.get("instructor"))
			if not current.get("room") and row.get("room"):
				current["room"] = row.get("room")

	result = []
	for row in by_key.values():
		instructors = sorted(row.pop("instructors"))
		row["instructor"] = instructors[0] if len(instructors) == 1 else None
		row["instructor_mapping_status"] = (
			"Resolved" if len(instructors) == 1 else "Missing" if not instructors else "Conflicting"
		)
		result.append(row)
	return result


def _scheduled_assignment(student_group, academic_year, course):
	"""Resolve one authoritative instructor from matching Course Schedules."""
	rows = _deduplicate_candidates(
		_course_schedule_candidates([student_group], academic_year, course)
	)
	if not rows:
		return frappe._dict(
			student_group=student_group,
			course=course,
			instructor=None,
			room=None,
			instructor_mapping_status="Missing",
		)
	return frappe._dict(rows[0])


def _validate_school_term(school_term, academic_year):
	term_year = frappe.db.get_value("School Term", school_term, "academic_year")
	if term_year and term_year != academic_year:
		frappe.throw(
			_("School Term {0} belongs to Academic Year {1}, not {2}.").format(
				school_term, term_year, academic_year
			)
		)


def _existing_plan(student_group, course, assessment_group, academic_year):
	return frappe.db.get_value(
		"Assessment Plan",
		{
			"student_group": student_group,
			"course": course,
			"assessment_group": assessment_group,
			"academic_year": academic_year,
			"docstatus": ["<", 2],
		},
	)


@frappe.whitelist()
def get_setup_candidates(
	academic_year,
	school_term,
	assessment_group,
	course,
	program=None,
	student_batch=None,
	exam_paper_requirement=None,
):
	frappe.only_for(("Education Manager", "System Manager"))
	_validate_school_term(school_term, academic_year)
	if exam_paper_requirement:
		requirement = frappe.get_doc("Exam Paper Requirement", exam_paper_requirement)
		requirement.check_permission("read")
		if requirement.status not in {"Approved", "Plans Partially Created", "Complete"}:
			frappe.throw(_("The Exam Paper Requirement must have final approval before creating Assessment Plans."))
		expected = {
			"academic_year": academic_year,
			"school_term": school_term,
			"assessment_group": assessment_group,
			"course": course,
			"student_batch": student_batch,
		}
		for fieldname, value in expected.items():
			if value and requirement.get(fieldname) != value:
				frappe.throw(_("The setup value for {0} does not match the approved paper requirement.").format(fieldname))
		rows = []
		for affected in requirement.affected_student_groups:
			existing = _existing_plan(affected.student_group, course, assessment_group, academic_year)
			assignment = _scheduled_assignment(affected.student_group, academic_year, course)
			rows.append(
				{
					"student_group": affected.student_group,
					"course": course,
					"instructor": assignment.instructor,
					"instructor_mapping_status": assignment.instructor_mapping_status,
					"room": requirement.room or assignment.room,
					"existing_plan": existing,
					"create_plan": 0 if existing else 1,
				}
			)
		return {
			"rows": rows,
			"group_count": len(rows),
			"criteria": [
				{
					"assessment_criteria": row.assessment_criteria,
					"maximum_score": row.maximum_score,
				}
				for row in requirement.assessment_criteria
			],
			"schedule_defaults": {
				"schedule_date": requirement.examination_date,
				"from_time": requirement.from_time,
				"to_time": requirement.to_time,
				"room": requirement.room,
				"grading_scale": requirement.grading_scale,
			},
			"message": _(
				"Loaded the approved paper, structured criteria, and exact affected Student Groups from {0}."
			).format(requirement.name),
		}

	group_fields = _meta_fields("Student Group")
	query_fields = ["name"]
	if "course" in group_fields:
		query_fields.append("course")
	groups = frappe.get_all(
		"Student Group",
		filters=_group_filters(academic_year, program, student_batch),
		fields=query_fields,
		order_by="name asc",
	)
	group_names = [row.name for row in groups]
	candidates = _deduplicate_candidates(
		_course_schedule_candidates(group_names, academic_year, course) + _group_course_candidates(groups, course)
	)

	for row in candidates:
		row["existing_plan"] = _existing_plan(
			row["student_group"], row["course"], assessment_group, academic_year
		)
		row["create_plan"] = 0 if row["existing_plan"] else 1

	return {
		"rows": candidates,
		"group_count": len(group_names),
		"message": _(
			"Candidates come from Course Schedules and course-based Student Groups. Add any missing group/course pair manually. The Instructor is the course/examiner reference on the standard plan; exam supervisors will be managed separately."
		),
	}


def _validate_criteria(criteria):
	criteria = _as_list(criteria)
	if not criteria:
		frappe.throw(_("Add at least one Assessment Criterion."))

	cleaned = []
	seen = set()
	for row in criteria:
		criterion = row.get("assessment_criteria")
		maximum_score = flt(row.get("maximum_score"))
		if not criterion:
			frappe.throw(_("Every criteria row must select an Assessment Criterion."))
		if criterion in seen:
			frappe.throw(_("Assessment Criterion {0} is listed more than once.").format(criterion))
		if maximum_score <= 0:
			frappe.throw(_("Maximum Score for {0} must be greater than zero.").format(criterion))
		seen.add(criterion)
		cleaned.append({"assessment_criteria": criterion, "maximum_score": maximum_score})
	return cleaned


def _validate_plan_rows(rows, academic_year):
	rows = _as_list(rows)
	cleaned = []
	seen = set()
	for row in rows:
		if not int(row.get("create_plan") or 0):
			continue
		student_group = row.get("student_group")
		course = row.get("course")
		if not student_group or not course:
			frappe.throw(_("Every selected row must contain a Student Group and Course."))
		key = (student_group, course)
		if key in seen:
			frappe.throw(_("Student Group {0} and Course {1} are listed more than once.").format(*key))
		seen.add(key)
		group_year = frappe.db.get_value("Student Group", student_group, "academic_year")
		if group_year and group_year != academic_year:
			frappe.throw(
				_("Student Group {0} belongs to Academic Year {1}, not {2}.").format(
					student_group, group_year, academic_year
				)
			)
		cleaned.append(row)
	if not cleaned:
		frappe.throw(_("Select at least one missing Assessment Plan to create."))
	return cleaned


def _required_plan_fields_missing(plan_meta, values):
	missing = []
	for field in plan_meta.fields:
		if not field.reqd or field.fieldtype in {"Section Break", "Column Break", "Tab Break", "Table"}:
			continue
		if field.fieldname not in values and not field.default:
			missing.append(field.label or field.fieldname)
	return missing


def _build_plan_values(args, row, criteria, plan_meta):
	plan_fields = {field.fieldname for field in plan_meta.fields}
	maximum_score = sum(flt(item["maximum_score"]) for item in criteria)
	values = {
		"academic_year": args.get("academic_year"),
		"assessment_group": args.get("assessment_group"),
		"assessment_name": "{0} - {1} - {2}".format(
			args.get("assessment_group"), row.get("course"), row.get("student_group")
		),
		"course": row.get("course"),
		"from_time": args.get("from_time"),
		"grading_scale": args.get("grading_scale"),
		"instructor": row.get("instructor"),
		"maximum_assessment_score": maximum_score,
		"room": row.get("room") or args.get("room"),
		"schedule_date": args.get("schedule_date"),
		"student_group": row.get("student_group"),
		"to_time": args.get("to_time"),
	}
	return {key: value for key, value in values.items() if key in plan_fields and value not in (None, "")}


@frappe.whitelist()
def create_assessment_plans(setup, rows, criteria):
	frappe.only_for(("Education Manager", "System Manager"))
	args = frappe._dict(json.loads(setup) if isinstance(setup, str) else setup)
	for required in ("academic_year", "school_term", "assessment_group", "course", "schedule_date"):
		if not args.get(required):
			frappe.throw(_("{0} is required.").format(required.replace("_", " ").title()))

	_validate_school_term(args.school_term, args.academic_year)
	source_requirement = None
	if args.get("exam_paper_requirement"):
		source_requirement = frappe.get_doc("Exam Paper Requirement", args.exam_paper_requirement)
		if source_requirement.status not in {"Approved", "Plans Partially Created", "Complete"}:
			frappe.throw(_("The linked Exam Paper Requirement is not approved."))
	criteria = _validate_criteria(criteria)
	rows = _validate_plan_rows(rows, args.academic_year)
	if source_requirement:
		approved_criteria = [
			{"assessment_criteria": row.assessment_criteria, "maximum_score": flt(row.maximum_score)}
			for row in source_requirement.assessment_criteria
		]
		if criteria != approved_criteria:
			frappe.throw(_("Assessment Criteria must match the approved Exam Paper Requirement."))
		allowed_groups = {row.student_group for row in source_requirement.affected_student_groups}
		unexpected_groups = {row.get("student_group") for row in rows} - allowed_groups
		if unexpected_groups:
			frappe.throw(
				_("The selected Student Groups are not part of the approved paper requirement: {0}.").format(
					", ".join(sorted(unexpected_groups))
				)
			)
		for row in rows:
			assignment = _scheduled_assignment(row.get("student_group"), args.academic_year, args.course)
			if assignment.instructor_mapping_status == "Missing":
				frappe.throw(
					_("Student Group {0} has no Course Schedule instructor for {1}. Correct the Course Schedule before creating its Assessment Plan.").format(
						row.get("student_group"), args.course
					)
				)
			if assignment.instructor_mapping_status == "Conflicting":
				frappe.throw(
					_("Student Group {0} has different instructors scheduled for {1}. Correct the Course Schedules so responsibility is unambiguous.").format(
						row.get("student_group"), args.course
					)
				)
			row["instructor"] = assignment.instructor
			row["instructor_mapping_status"] = assignment.instructor_mapping_status
	for row in rows:
		if row.get("course") != args.course:
			frappe.throw(
				_("Every selected row must use the exam Course {0}. Found {1} in Student Group {2}.").format(
					args.course, row.get("course"), row.get("student_group")
				)
			)
	plan_meta = frappe.get_meta("Assessment Plan")
	criteria_field = plan_meta.get_field("assessment_criteria")
	if not criteria_field or criteria_field.fieldtype != "Table":
		frappe.throw(_("The installed Education app does not expose Assessment Plan criteria as expected."))

	created = []
	submitted = []
	skipped = []
	auto_submit = bool(
		source_requirement
		and cint(frappe.db.get_single_value(
			"School MIS Settings", "submit_assessment_plans_from_exam_requirements"
		))
	)
	if auto_submit and not plan_meta.is_submittable:
		frappe.throw(_("Assessment Plan is not submittable in the installed Education version."))
	for row in rows:
		existing = _existing_plan(
			row.get("student_group"), row.get("course"), args.assessment_group, args.academic_year
		)
		if existing:
			skipped.append(existing)
			continue

		values = _build_plan_values(args, row, criteria, plan_meta)
		missing = _required_plan_fields_missing(plan_meta, values)
		if missing:
			frappe.throw(
				_("Cannot bulk-create Assessment Plans because this Education version also requires: {0}.").format(
					", ".join(missing)
				)
			)

		doc = frappe.new_doc("Assessment Plan")
		doc.update(values)
		for criterion in criteria:
			doc.append("assessment_criteria", criterion)
		doc.insert()
		created.append(doc.name)
		if auto_submit:
			doc.submit()
			submitted.append(doc.name)
		if source_requirement:
			from high_school.high_school.result_submission import sync_tracker_for_assessment_plan

			sync_tracker_for_assessment_plan(
				doc,
				exam_paper_requirement=source_requirement.name,
			)

	result = {"created": created, "submitted": submitted, "skipped": skipped}
	if args.get("exam_paper_requirement"):
		requirement = frappe.get_doc("Exam Paper Requirement", args.exam_paper_requirement)
		requirement.update_plan_coverage()
		requirement.add_activity("Assessment Plan coverage refreshed")
		requirement.save(ignore_permissions=True)
		result["requirement_status"] = requirement.status
	return result
