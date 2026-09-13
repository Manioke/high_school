"""Parent-led admission, guardian account, and guardian fee access workflows."""

from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import add_to_date, cint, escape_html, formatdate, get_request_session, now_datetime, today, validate_email_address


PARENT_NAME_FIELD = "custom_parentguardian_name"
PARENT_EMAIL_FIELD = "custom_parentguardian_email"
PARENT_RELATION_FIELD = "custom_parentguardian_relation"
APPLICANT_BATCH_FIELD = "custom_student_batch_name"
TURNSTILE_TOKEN_FIELD = "custom_registration_verification_token"
HONEYPOT_FIELD = "custom_registration_website"
BATCH_PROGRAM_FIELD = "custom_program"
DEFAULT_TURNSTILE_SITE_KEY = "0x4AAAAAAEyC-Z8GCHiJAmgp"
TURNSTILE_ACTION = "student_admission"


def _meta_fields(doctype):
	return {field.fieldname for field in frappe.get_meta(doctype).fields}


def _upsert_custom_field(dt, fieldname, **values):
	name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, "name")
	payload = {"module": "High School", **values}
	if name:
		doc = frappe.get_doc("Custom Field", name)
		changed = False
		for key, value in payload.items():
			if doc.get(key) != value:
				doc.set(key, value)
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
		return doc
	return frappe.get_doc({"doctype": "Custom Field", "dt": dt, "fieldname": fieldname, **payload}).insert(ignore_permissions=True)


def _first_existing(doctype, *fieldnames):
	fields = _meta_fields(doctype)
	return next((fieldname for fieldname in fieldnames if fieldname in fields), None)


def _make_student_email_optional(doctype):
	for fieldname in ("student_email_id", "student_email"):
		if fieldname in _meta_fields(doctype):
			make_property_setter(doctype, fieldname, "reqd", 0, "Check", validate_fields_for_doctype=False)


def _ensure_guardian_profiles():
	if frappe.db.exists("Role Profile", "Guardian Role Profile"):
		profile = frappe.get_doc("Role Profile", "Guardian Role Profile")
		if [row.role for row in profile.roles] != ["Guardian"]:
			profile.set("roles", [])
			profile.append("roles", {"role": "Guardian"})
			profile.save(ignore_permissions=True)
	else:
		profile = frappe.new_doc("Role Profile")
		profile.role_profile = "Guardian Role Profile"
		profile.append("roles", {"role": "Guardian"})
		profile.insert(ignore_permissions=True)
	if frappe.db.exists("Module Profile", "Guardian Module Profile"):
		profile = frappe.get_doc("Module Profile", "Guardian Module Profile")
		for fieldname in ("modules", "block_modules"):
			if profile.meta.has_field(fieldname) and profile.get(fieldname):
				profile.set(fieldname, [])
				profile.save(ignore_permissions=True)
	else:
		profile = frappe.new_doc("Module Profile")
		profile.module_profile_name = "Guardian Module Profile"
		# Intentionally no modules selected. Website User status is the Desk boundary.
		profile.insert(ignore_permissions=True)


def _repair_invalid_guardian_relations():
	if not frappe.db.table_exists("Student Guardian"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabStudent Guardian`
		SET relation = 'Others'
		WHERE COALESCE(relation, '') NOT IN ('', 'Mother', 'Father', 'Others')
		"""
	)


def _ensure_admission_web_form_fields():
	for name in frappe.get_all("Web Form", filters={"doc_type": "Student Applicant"}, pluck="name", limit_page_length=0):
		web_form = frappe.get_doc("Web Form", name)
		# Public applicants must never browse or select existing Guardian master records.
		web_form.set(
			"web_form_fields",
			[
				row for row in web_form.web_form_fields
				if row.fieldname not in {"guardians", "custom_application_type", "custom_student_id"}
			],
		)
		for row in web_form.web_form_fields:
			if row.fieldname in {"student_email_id", "student_email"}:
				row.reqd = 0
		definitions = [
			("custom_parentguardian_section", "Parent / Guardian Details", "Section Break", None, 0),
			(PARENT_NAME_FIELD, "Parent / Guardian Name", "Data", None, 1),
			(PARENT_EMAIL_FIELD, "Parent / Guardian Email", "Data", "Email", 1),
			(PARENT_RELATION_FIELD, "Relationship to Student", "Select", "Mother\nFather\nOthers", 1),
			(APPLICANT_BATCH_FIELD, "Student Batch", "Link", "Student Batch Name", 1),
			(HONEYPOT_FIELD, "Website", "Data", None, 0),
			(TURNSTILE_TOKEN_FIELD, "Registration Verification", "Small Text", None, 0),
		]
		for fieldname, label, fieldtype, options, reqd in definitions:
			row = next((item for item in web_form.web_form_fields if item.fieldname == fieldname), None)
			if not row:
				row = web_form.append("web_form_fields", {
					"fieldname": fieldname,
				})
			row.label = label
			row.fieldtype = fieldtype
			row.options = options
			row.reqd = reqd
			if fieldname in {HONEYPOT_FIELD, TURNSTILE_TOKEN_FIELD}:
				row.hidden = 1
		for row in web_form.web_form_fields:
			if row.fieldname in {HONEYPOT_FIELD, TURNSTILE_TOKEN_FIELD}:
				row.hidden = 1
		web_form.save(ignore_permissions=True)


def _normalise_guardian_relation(value):
	value = (value or "").strip().title()
	return value if value in {"Mother", "Father", "Others"} else "Others"


def _public_submission_rate_limit():
	settings = frappe.get_cached_doc("School MIS Settings")
	limit = max(cint(settings.get("public_admission_hourly_limit")) or 20, 1)
	request_ip = getattr(frappe.local, "request_ip", None) or "unknown"
	identity = hashlib.sha256(request_ip.encode("utf-8")).hexdigest()
	cache_key = frappe.cache.make_key(f"high_school:public_admission:{identity}")
	if not frappe.cache.get(cache_key):
		frappe.cache.setex(cache_key, 3600, 0)
	count = frappe.cache.incrby(cache_key, 1)
	if count > limit:
		frappe.throw(
			_("Too many applications were submitted from this connection. Please try again later."),
			frappe.RateLimitExceededError,
		)


def _verify_turnstile(doc):
	settings = frappe.get_cached_doc("School MIS Settings")
	if not cint(settings.get("enable_public_admission_turnstile")):
		return
	secret = settings.get_password("turnstile_secret_key", raise_exception=False)
	token = (doc.get(TURNSTILE_TOKEN_FIELD) or "").strip()
	allowed_hostnames = {
		hostname.strip().lower()
		for hostname in (settings.get("turnstile_allowed_hostnames") or "").split(",")
		if hostname.strip()
	}
	if not secret or not settings.get("turnstile_site_key"):
		frappe.throw(_("Public admission verification is enabled but has not been configured by the school."))
	if not token or len(token) > 2048 or not allowed_hostnames:
		frappe.throw(_("Please complete the security verification before submitting the application."))

	try:
		verification_response = get_request_session().post(
			"https://challenges.cloudflare.com/turnstile/v0/siteverify",
			data={
				"secret": secret,
				"response": token,
				"remoteip": getattr(frappe.local, "request_ip", None),
			},
			timeout=10,
		)
		verification_response.raise_for_status()
		response = verification_response.json()
	except Exception:
		frappe.log_error(title="Student admission Turnstile verification failed")
		frappe.throw(_("The security verification service could not be reached. Please try again."))
	if (
		not isinstance(response, dict)
		or not response.get("success")
		or response.get("action") != TURNSTILE_ACTION
		or (response.get("hostname") or "").lower() not in allowed_hostnames
	):
		frappe.throw(_("Security verification failed. Please refresh the page and try again."))


def _reject_duplicate_public_application(doc):
	fields = _meta_fields("Student Applicant")
	filters = {
		PARENT_EMAIL_FIELD: (doc.get(PARENT_EMAIL_FIELD) or "").strip().lower(),
		"creation": [">=", add_to_date(now_datetime(), hours=-24)],
	}
	for fieldname in ("academic_year", "program", "first_name", "last_name", "date_of_birth"):
		if fieldname in fields and doc.get(fieldname):
			filters[fieldname] = doc.get(fieldname)
	if "application_status" in fields:
		filters["application_status"] = ["!=", "Rejected"]
	if frappe.db.exists("Student Applicant", filters):
		frappe.throw(
			_("An application for this student was already received recently. Please contact the school if you need to change it."),
			frappe.DuplicateEntryError,
		)


def validate_public_student_application(doc, method=None):
	"""Apply public-form abuse controls without affecting trusted Desk entry."""
	if str(doc.get("application_date") or "").strip().lower() == "today":
		doc.application_date = today()
	if not getattr(frappe.flags, "in_web_form", False) or frappe.session.user != "Guest":
		return
	doc.flags.public_student_application = True
	if doc.get(HONEYPOT_FIELD):
		frappe.throw(_("The application could not be accepted. Please refresh the page and try again."))
	_public_submission_rate_limit()
	doc.set(PARENT_NAME_FIELD, (doc.get(PARENT_NAME_FIELD) or "").strip())
	doc.set(PARENT_EMAIL_FIELD, (doc.get(PARENT_EMAIL_FIELD) or "").strip().lower())
	doc.set(PARENT_RELATION_FIELD, _normalise_guardian_relation(doc.get(PARENT_RELATION_FIELD)))
	validate_email_address(doc.get(PARENT_EMAIL_FIELD), throw=True)
	_verify_turnstile(doc)
	_reject_duplicate_public_application(doc)
	# Verification evidence is single-use and must never be retained in the Applicant.
	doc.set(TURNSTILE_TOKEN_FIELD, "")
	doc.set(HONEYPOT_FIELD, "")


def queue_application_receipt_email(doc, method=None):
	"""Send a receipt only for an application accepted through the public Web Form."""
	if not doc.flags.get("public_student_application") or not doc.get(PARENT_EMAIL_FIELD):
		return
	frappe.enqueue(
		"high_school.high_school.admissions.send_application_receipt_email",
		queue="short",
		enqueue_after_commit=True,
		applicant=doc.name,
	)


def send_application_receipt_email(applicant):
	doc = frappe.get_doc("Student Applicant", applicant)
	parent = escape_html(doc.get(PARENT_NAME_FIELD) or _("Parent / Guardian"))
	student_label = doc.get("title") or doc.get("student_name") or doc.name
	student = escape_html(student_label)
	details = [
		(_("Application ID"), doc.name),
		(_("Student"), student_label),
		(_("Program"), doc.get("program") or _("Not specified")),
		(_("Academic Year"), doc.get("academic_year") or _("Not specified")),
		(_("Student Batch"), doc.get(APPLICANT_BATCH_FIELD) or _("Not specified")),
		(_("Application Date"), formatdate(doc.get("application_date") or doc.creation)),
	]
	rows = "".join(
		f"<tr><td style='padding:4px 12px 4px 0'><strong>{escape_html(str(label))}</strong></td>"
		f"<td style='padding:4px 0'>{escape_html(str(value))}</td></tr>"
		for label, value in details
	)
	frappe.sendmail(
		recipients=[doc.get(PARENT_EMAIL_FIELD)],
		subject=_("Application received: {0}").format(student_label),
		message=_("""
			<p>Dear {parent},</p>
			<p>Thank you. The school has received the following student application:</p>
			<table>{rows}</table>
			<p>The school will review the application and contact you using this email address. Please keep the Application ID for reference.</p>
		""").format(parent=parent, rows=rows),
		reference_doctype="Student Applicant",
		reference_name=doc.name,
	)


@frappe.whitelist(allow_guest=True)
def get_public_admission_security_config():
	settings = frappe.get_cached_doc("School MIS Settings")
	enabled = bool(cint(settings.get("enable_public_admission_turnstile")))
	return {
		"enabled": enabled,
		"site_key": settings.get("turnstile_site_key") if enabled else None,
		"action": TURNSTILE_ACTION if enabled else None,
	}


@frappe.whitelist(allow_guest=True)
def get_public_student_batches(program=None):
	"""Return only reusable batch names owned by the selected Program."""
	if not program or not frappe.db.exists("Program", program):
		return []
	if BATCH_PROGRAM_FIELD not in _meta_fields("Student Batch Name"):
		return []
	return frappe.get_all(
		"Student Batch Name",
		filters={BATCH_PROGRAM_FIELD: program},
		pluck="name",
		order_by="name asc",
		limit_page_length=0,
		ignore_permissions=True,
	)


@frappe.whitelist()
def enroll_student_with_batch(source_name):
	"""Preserve the Applicant's batch when using the built-in Enroll action."""
	applicant = frappe.get_doc("Student Applicant", source_name)
	applicant.check_permission("write")
	if applicant.get("application_status") != "Approved":
		frappe.throw(_("Student Applicant {0} must be Approved before enrollment.").format(applicant.name))

	batch = applicant.get(APPLICANT_BATCH_FIELD)
	if not batch:
		frappe.throw(_("Student Batch is required on Student Applicant {0}.").format(applicant.name))
	validate_applicant_program_batch(applicant)

	student = find_existing_student_for_applicant(applicant)
	if student:
		existing = frappe.db.get_value(
			"Program Enrollment",
			{
				"student": student,
				"program": applicant.program,
				"academic_year": applicant.academic_year,
				"docstatus": ["<", 2],
			},
			"name",
		)
		if existing:
			frappe.throw(_("Program Enrollment {0} already exists for this student, program and academic year.").format(existing))
		enrollment = frappe.new_doc("Program Enrollment")
		enrollment.student = student
		enrollment.student_name = frappe.db.get_value("Student", student, "student_name")
		enrollment.program = applicant.program
		enrollment.academic_year = applicant.academic_year
		enrollment.academic_term = applicant.get("academic_term")
		enrollment.enrollment_date = today()
	else:
		from education.education.api import enroll_student

		enrollment = enroll_student(source_name)

	enrollment.student_batch_name = batch
	if applicant.get("student_category"):
		enrollment.student_category = applicant.student_category
	if enrollment.meta.has_field("custom_student_applicant"):
		enrollment.custom_student_applicant = applicant.name
	enrollment.save(ignore_permissions=True)
	return enrollment


def setup_admission_and_guardian_workflow():
	"""Install portable admission fields and portal-safe defaults after migrate."""
	insert_after = _first_existing("Student Applicant", "student_email_id", "student_email", "last_name") or "last_name"
	_upsert_custom_field(
		"Student Batch Name", BATCH_PROGRAM_FIELD,
		label="Program", fieldtype="Link", options="Program", insert_after="batch_name", reqd=1,
		allow_in_quick_entry=1, in_list_view=1, in_standard_filter=1,
		description="Program that owns this reusable Form/Batch name, such as High School, Middle School, or Kindergarten.",
	)
	_upsert_custom_field(
		"Student Applicant", "custom_parentguardian_section",
		label="Parent / Guardian Details", fieldtype="Section Break", insert_after=insert_after,
	)
	_upsert_custom_field(
		"Student Applicant", PARENT_NAME_FIELD,
		label="Parent / Guardian Name", fieldtype="Data", insert_after="custom_parentguardian_section", reqd=1,
		description="Full name of the adult submitting the application. A Guardian record is created only after enrollment.",
	)
	_upsert_custom_field(
		"Student Applicant", PARENT_EMAIL_FIELD,
		label="Parent / Guardian Email", fieldtype="Data", options="Email", insert_after=PARENT_NAME_FIELD,
		reqd=1, unique=0,
		description="Used for approval notices, the Guardian portal account, invoices and school communication. It is not unique because one parent may apply for several children.",
	)
	_upsert_custom_field(
		"Student Applicant", PARENT_RELATION_FIELD,
		label="Relationship to Student", fieldtype="Select", options="Mother\nFather\nOthers",
		insert_after=PARENT_EMAIL_FIELD, reqd=1,
		description="Relationship of the registering Guardian to the student.",
	)
	_upsert_custom_field(
		"Student Applicant", APPLICANT_BATCH_FIELD,
		label="Student Batch", fieldtype="Link", options="Student Batch Name", insert_after=PARENT_RELATION_FIELD,
		reqd=1,
		description="Transferred automatically to Program Enrollment.",
	)
	_upsert_custom_field(
		"Student Applicant", HONEYPOT_FIELD,
		label="Website", fieldtype="Data", insert_after=APPLICANT_BATCH_FIELD, hidden=1,
		description="Automated abuse-detection field. Leave empty.",
	)
	_upsert_custom_field(
		"Student Applicant", TURNSTILE_TOKEN_FIELD,
		label="Registration Verification", fieldtype="Small Text", insert_after=HONEYPOT_FIELD,
		hidden=1, no_copy=1,
	)
	_upsert_custom_field(
		"Program Enrollment", "custom_student_applicant",
		label="Source Student Applicant", fieldtype="Link", options="Student Applicant", insert_after="student", read_only=1,
	)
	for fieldname in ("custom_application_type", "custom_student_id"):
		name = frappe.db.get_value("Custom Field", {"dt": "Student Applicant", "fieldname": fieldname}, "name")
		if name:
			legacy = frappe.get_doc("Custom Field", name)
			legacy.hidden = 1
			legacy.reqd = 0
			legacy.mandatory_depends_on = None
			legacy.save(ignore_permissions=True)
	_make_student_email_optional("Student")
	_make_student_email_optional("Student Applicant")
	_ensure_guardian_profiles()
	_repair_invalid_guardian_relations()
	_ensure_admission_web_form_fields()
	if not frappe.db.get_single_value("School MIS Settings", "turnstile_site_key"):
		frappe.db.set_single_value("School MIS Settings", "turnstile_site_key", DEFAULT_TURNSTILE_SITE_KEY)
	if not frappe.db.get_single_value("School MIS Settings", "turnstile_allowed_hostnames"):
		frappe.db.set_single_value(
			"School MIS Settings",
			"turnstile_allowed_hostnames",
			"development.localhost,localhost,127.0.0.1",
		)
	frappe.clear_cache(doctype="Student Applicant")
	frappe.clear_cache(doctype="Student")
	frappe.clear_cache(doctype="School MIS Settings")
	frappe.db.commit()


def validate_applicant_program_batch(doc, method=None):
	batch = doc.get(APPLICANT_BATCH_FIELD)
	if not batch or not doc.get("program") or BATCH_PROGRAM_FIELD not in _meta_fields("Student Batch Name"):
		return
	batch_program = frappe.db.get_value("Student Batch Name", batch, BATCH_PROGRAM_FIELD)
	if batch_program and batch_program != doc.program:
		frappe.throw(_("Student Batch {0} belongs to Program {1}, not {2}.").format(batch, batch_program, doc.program))


def find_existing_student_for_applicant(applicant):
	"""Return one strongly matched Student, or None. Never guess between duplicates."""
	legacy = applicant.get("custom_student_id")
	if legacy and frappe.db.exists("Student", legacy):
		return legacy
	student_fields = _meta_fields("Student")
	filters = {}
	for fieldname in ("first_name", "last_name", "date_of_birth", "gender"):
		if fieldname in student_fields and applicant.get(fieldname):
			filters[fieldname] = applicant.get(fieldname)
	if not filters.get("first_name") or not filters.get("date_of_birth"):
		return None
	candidates = set(frappe.get_all("Student", filters=filters, pluck="name", limit_page_length=0))
	if not candidates:
		return None
	parent_email = (applicant.get(PARENT_EMAIL_FIELD) or "").strip().lower()
	linked = set(_guardian_students(parent_email)) if parent_email and frappe.db.exists("User", parent_email) else set()
	linked_matches = candidates.intersection(linked)
	if len(linked_matches) == 1:
		return next(iter(linked_matches))
	if len(candidates) == 1:
		return next(iter(candidates))
	frappe.throw(
		_("More than one existing Student matches this applicant. School staff must review the records before enrollment."),
		title=_("Ambiguous Existing Student"),
	)


def handle_applicant_approval(doc, method=None):
	"""Queue one parent notice when an applicant first becomes Approved."""
	if doc.get("application_status") != "Approved":
		return
	before = doc.get_doc_before_save()
	if before and before.get("application_status") == "Approved":
		return
	existing_student = find_existing_student_for_applicant(doc)
	if existing_student:
		updates = {}
		if "custom_student_id" in _meta_fields("Student Applicant"):
			updates["custom_student_id"] = existing_student
		if "custom_application_type" in _meta_fields("Student Applicant"):
			updates["custom_application_type"] = "Old Student"
		if updates:
			frappe.db.set_value("Student Applicant", doc.name, updates, update_modified=False)
	email = doc.get(PARENT_EMAIL_FIELD)
	if not email:
		return
	frappe.enqueue(
		"high_school.high_school.admissions.send_applicant_approval_email",
		queue="short",
		enqueue_after_commit=True,
		applicant=doc.name,
	)


def send_applicant_approval_email(applicant):
	doc = frappe.get_doc("Student Applicant", applicant)
	parent = escape_html(doc.get(PARENT_NAME_FIELD) or _("Parent / Guardian"))
	student = escape_html(doc.get("title") or doc.get("student_name") or doc.name)
	batch = escape_html(doc.get(APPLICANT_BATCH_FIELD) or _("To be confirmed"))
	frappe.sendmail(
		recipients=[doc.get(PARENT_EMAIL_FIELD)],
		subject=_("Student application approved: {0}").format(student),
		message=_("""
			<p>Dear {parent},</p>
			<p>The application for <strong>{student}</strong> has been approved.</p>
			<p>Planned student batch: <strong>{batch}</strong>. The school is now completing enrollment.</p>
			<p>After enrollment, you will receive the class/group details, fee invoice information, and access instructions for the Parent/Guardian portal.</p>
		""").format(parent=parent, student=student, batch=batch),
		reference_doctype="Student Applicant",
		reference_name=doc.name,
	)


def _source_applicant(enrollment):
	if enrollment.get("custom_student_applicant"):
		return enrollment.custom_student_applicant
	student_fields = _meta_fields("Student")
	for fieldname in ("student_applicant", "student_applicant_id"):
		if fieldname in student_fields:
			value = frappe.db.get_value("Student", enrollment.student, fieldname)
			if value:
				return value
	return None


def _ensure_guardian_user(email, full_name):
	validate_email_address(email, throw=True)
	name = email.strip().lower()
	if frappe.db.exists("User", name):
		user = frappe.get_doc("User", name)
		if not user.enabled:
			user.enabled = 1
		# Do not demote an existing staff System User. Existing portal users can
		# safely receive the dedicated Guardian profiles.
		if user.get("user_type") == "Website User":
			user.role_profile_name = "Guardian Role Profile"
			if user.meta.has_field("module_profile"):
				user.module_profile = "Guardian Module Profile"
			if user.meta.has_field("redirect_url"):
				user.redirect_url = "/edu-portal"
		elif not any(row.role == "Guardian" for row in user.roles):
			user.append("roles", {"role": "Guardian"})
		user.save(ignore_permissions=True)
		return user

	parts = full_name.split(None, 1)
	user = frappe.get_doc({
		"doctype": "User",
		"email": name,
		"first_name": parts[0] if parts else full_name,
		"last_name": parts[1] if len(parts) > 1 else "",
		"enabled": 1,
		"user_type": "Website User",
		"send_welcome_email": 1,
		"role_profile_name": "Guardian Role Profile",
		"module_profile": "Guardian Module Profile",
		"redirect_url": "/edu-portal",
	})
	user.insert(ignore_permissions=True)
	return user


def _ensure_guardian(email, full_name, user):
	fields = _meta_fields("Guardian")
	for fieldname in ("user_id", "user"):
		if fieldname in fields:
			name = frappe.db.get_value("Guardian", {fieldname: user.name}, "name")
			if name:
				return frappe.get_doc("Guardian", name)
	for fieldname in ("email_address", "email"):
		if fieldname in fields:
			name = frappe.db.get_value("Guardian", {fieldname: email}, "name")
			if name:
				guardian = frappe.get_doc("Guardian", name)
				user_field = "user_id" if "user_id" in fields else "user" if "user" in fields else None
				if user_field and not guardian.get(user_field):
					guardian.set(user_field, user.name)
					guardian.save(ignore_permissions=True)
				return guardian

	guardian = frappe.new_doc("Guardian")
	guardian.guardian_name = full_name
	if "user_id" in fields:
		guardian.user_id = user.name
	elif "user" in fields:
		guardian.user = user.name
	if "email_address" in fields:
		guardian.email_address = email
	elif "email" in fields:
		guardian.email = email
	guardian.insert(ignore_permissions=True)
	return guardian


def _link_guardian_to_student(student_name, guardian, relation=None):
	student = frappe.get_doc("Student", student_name)
	relation = _normalise_guardian_relation(relation)
	for row in student.get("guardians") or []:
		if row.guardian != guardian.name:
			continue
		if row.get("relation") not in {"Mother", "Father", "Others"}:
			row.relation = relation
			student.save(ignore_permissions=True)
		return
	student.append("guardians", {
		"guardian": guardian.name,
		"guardian_name": guardian.guardian_name,
		"relation": relation,
	})
	student.save(ignore_permissions=True)


def complete_guardian_enrollment(enrollment, method=None):
	"""Create/reuse the parent account and link it after Program Enrollment submits."""
	if not enrollment.get("student"):
		return
	applicant_name = _source_applicant(enrollment)
	if not applicant_name or not frappe.db.exists("Student Applicant", applicant_name):
		return
	applicant = frappe.get_doc("Student Applicant", applicant_name)
	email = (applicant.get(PARENT_EMAIL_FIELD) or "").strip().lower()
	full_name = (applicant.get(PARENT_NAME_FIELD) or "").strip()
	if not email or not full_name:
		frappe.log_error(
			title=f"Guardian setup skipped for {enrollment.name}",
			message=f"Student Applicant {applicant.name} is missing Parent/Guardian Name or Email.",
		)
		return
	user = _ensure_guardian_user(email, full_name)
	guardian = _ensure_guardian(email, full_name, user)
	_link_guardian_to_student(
		enrollment.student,
		guardian,
		applicant.get(PARENT_RELATION_FIELD),
	)
	frappe.enqueue(
		"high_school.high_school.admissions.send_parent_enrollment_email",
		queue="short",
		enqueue_after_commit=True,
		applicant=applicant.name,
		student=enrollment.student,
		enrollment=enrollment.name,
	)


def _student_group_names(student):
	return frappe.get_all(
		"Student Group Student",
		filters={"student": student, "active": 1},
		pluck="parent",
		order_by="parent asc",
		limit_page_length=0,
	)


def _invoice_names_for_student(student):
	invoice_fields = _meta_fields("Sales Invoice")
	names = set()
	if "student" in invoice_fields:
		names.update(frappe.get_all("Sales Invoice", filters={"student": student, "docstatus": 1}, pluck="name", limit_page_length=0))
	if "customer" in invoice_fields and "customer" in _meta_fields("Student"):
		customer = frappe.db.get_value("Student", student, "customer")
		if customer:
			names.update(frappe.get_all("Sales Invoice", filters={"customer": customer, "docstatus": 1}, pluck="name", limit_page_length=0))
	return sorted(names)


def _invoice_rows_for_students(students):
	invoice_fields = _meta_fields("Sales Invoice")
	wanted = [field for field in ("name", "posting_date", "due_date", "grand_total", "outstanding_amount", "status", "currency", "customer", "student", "fee_schedule") if field in invoice_fields]
	rows = []
	for student in students:
		names = _invoice_names_for_student(student)
		for row in frappe.get_all("Sales Invoice", filters={"name": ["in", names]}, fields=wanted, order_by="due_date asc, name asc", limit_page_length=0) if names else []:
			row.student = student
			rows.append(row)
	return rows


def _guardian_students(user):
	guardian_fields = _meta_fields("Guardian")
	guardian_names = set()
	for fieldname in ("user_id", "user"):
		if fieldname in guardian_fields:
			guardian_names.update(frappe.get_all("Guardian", filters={fieldname: user}, pluck="name", limit_page_length=0))
	if not guardian_names:
		return []
	return sorted(set(frappe.get_all("Student Guardian", filters={"guardian": ["in", list(guardian_names)]}, pluck="parent", limit_page_length=0)))


@frappe.whitelist()
def get_guardian_student_invoices(student=None, student_id=None, **kwargs):
	"""Portal-safe invoice endpoint supporting Sales Invoice student or Customer links."""
	requested = student or student_id
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	privileged = {"Administrator", "System Manager", "Education Manager", "Accounts Manager", "Accounts User"}
	if roles.intersection(privileged) or user == "Administrator":
		students = [requested] if requested else []
	elif "Guardian" in roles:
		students = _guardian_students(user)
		if requested and requested not in students:
			frappe.throw(_("You can only view invoices for students linked to your Guardian account."), frappe.PermissionError)
		if requested:
			students = [requested]
	elif "Student" in roles:
		student_fields = _meta_fields("Student")
		user_field = next((field for field in ("user", "user_id", "student_email_id") if field in student_fields), None)
		own_student = frappe.db.get_value("Student", {user_field: user}, "name") if user_field else None
		if requested and requested != own_student:
			frappe.throw(_("You can only view your own invoices."), frappe.PermissionError)
		students = [own_student] if own_student else []
	else:
		frappe.throw(_("You do not have permission to view student invoices."), frappe.PermissionError)

	from education.education.api import (
		get_currency_symbol,
		get_fees_print_format,
		get_posting_date_from_payment_entry_against_sales_invoice,
		get_program_from_fee_schedule,
	)

	portal_invoices = []
	for row in _invoice_rows_for_students([value for value in students if value]):
		if row.get("status") not in {"Paid", "Unpaid", "Overdue", "Partly Paid"}:
			continue
		program = get_program_from_fee_schedule(row.get("fee_schedule")) if row.get("fee_schedule") else None
		if not program and row.get("student"):
			program = frappe.db.get_value(
				"Program Enrollment",
				{"student": row.student, "docstatus": 1},
				"program",
				order_by="academic_year desc, creation desc",
			)
		symbol = get_currency_symbol(row.get("currency") or "INR")
		amount = row.get("grand_total") if row.get("status") == "Paid" else row.get("outstanding_amount")
		portal_invoices.append({
			"status": row.get("status"),
			"program": program,
			"amount": f"{symbol} {amount or 0}",
			"invoice": row.name,
			"due_date": "-" if row.get("status") == "Paid" else (row.get("due_date") or "-"),
			"payment_date": (
				get_posting_date_from_payment_entry_against_sales_invoice(row.name) or "-"
				if row.get("status") == "Paid"
				else "-"
			),
		})
	return {
		"invoices": portal_invoices,
		"print_format": get_fees_print_format() or "Standard",
	}


def send_parent_enrollment_email(applicant, student, enrollment=None):
	applicant_doc = frappe.get_doc("Student Applicant", applicant)
	student_doc = frappe.get_doc("Student", student)
	enrollment_doc = frappe.get_doc("Program Enrollment", enrollment) if enrollment else None
	groups = _student_group_names(student)
	invoices = _invoice_rows_for_students([student])
	invoice_lines = "".join(
		f"<li>{escape_html(row.name)} — {escape_html(str(row.get('currency') or ''))} {row.get('grand_total') or 0:,.2f}; due {formatdate(row.get('due_date')) if row.get('due_date') else _('Not set')}</li>"
		for row in invoices
	) or f"<li>{_('No submitted fee invoice is available yet. The school will contact you when it is ready.')}</li>"
	frappe.sendmail(
		recipients=[applicant_doc.get(PARENT_EMAIL_FIELD)],
		subject=_("Enrollment completed: {0}").format(student_doc.student_name),
		message=_("""
			<p>Dear {parent},</p>
			<p><strong>{student}</strong> has been enrolled successfully.</p>
			<p><strong>Student ID:</strong> {student_id}<br>
			<strong>Student batch:</strong> {batch}<br>
			<strong>Student category:</strong> {category}<br>
			<strong>Student groups:</strong> {groups}</p>
			<p><strong>Fee information</strong></p><ul>{invoices}</ul>
			<p>Fee payments are made at the school office. Your Parent/Guardian portal account is linked to this student; use the separate welcome email to set your password and sign in.</p>
			<p><strong>Add the Parent Portal to your phone</strong></p>
			<ul>
				<li>Open <strong>{portal_url}</strong> in your phone browser and sign in.</li>
				<li>On Android/Chrome, open the browser menu and choose <strong>Add to Home screen</strong> or <strong>Install app</strong>.</li>
				<li>On iPhone/iPad Safari, tap <strong>Share</strong>, then <strong>Add to Home Screen</strong>.</li>
			</ul>
			<p>No app-store download is required. The secure school portal will open from the new home-screen icon.</p>
		""").format(
			parent=escape_html(applicant_doc.get(PARENT_NAME_FIELD)),
			student=escape_html(student_doc.student_name),
			student_id=escape_html(student_doc.name),
			batch=escape_html((enrollment_doc.get("student_batch_name") if enrollment_doc else None) or _("To be assigned")),
			category=escape_html((enrollment_doc.get("student_category") if enrollment_doc else None) or _("To be assigned")),
			groups=escape_html(", ".join(groups) or _("Assignment is being refreshed")),
			invoices=invoice_lines,
			portal_url=escape_html(frappe.utils.get_url("/edu-portal")),
		),
		reference_doctype="Student",
		reference_name=student,
	)
