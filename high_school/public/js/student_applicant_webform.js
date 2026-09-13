frappe.ready(async () => {
	const TOKEN_FIELD = "custom_registration_verification_token";
	const HONEYPOT_FIELD = "custom_registration_website";
	const PROGRAM_FIELD = "program";
	const BATCH_FIELD = "custom_student_batch_name";

	[TOKEN_FIELD, HONEYPOT_FIELD].forEach((fieldname) => {
		const control = frappe.web_form.fields_dict?.[fieldname];
		if (control?.wrapper) {
			$(control.wrapper).addClass("hide-control").hide();
		}
	});

	const applicationDate = frappe.web_form.fields_dict?.application_date;
	if (applicationDate && String(applicationDate.get_value() || "").toLowerCase() === "today") {
		applicationDate.set_value(frappe.datetime.get_today());
	}

	await refresh_batch_options();
	frappe.web_form.on(PROGRAM_FIELD, () => {
		const batch = frappe.web_form.fields_dict?.[BATCH_FIELD];
		if (batch?.get_value()) {
			batch.set_value("");
		}
		refresh_batch_options();
	});

	const response = await frappe.call({
		method: "high_school.high_school.admissions.get_public_admission_security_config",
	});
	const config = response.message || {};
	if (!config.enabled) {
		return;
	}
	if (!config.site_key) {
		frappe.msgprint(__("Online admission security has not been configured. Please contact the school."));
		$(".submit-btn").prop("disabled", true);
		return;
	}

	const verification = $(
		`<div class="high-school-admission-verification mb-3">
			<label class="control-label">${__("Security verification")}</label>
			<div class="turnstile-widget"></div>
		</div>`
	);
	$(".web-form-footer").before(verification);

	await load_turnstile_script();
	window.turnstile.render(verification.find(".turnstile-widget")[0], {
		sitekey: config.site_key,
		action: config.action || "student_admission",
		callback: (token) => set_verification_token(token),
		"expired-callback": () => set_verification_token(""),
		"error-callback": () => set_verification_token(""),
	});

	const originalValidate = frappe.web_form.validate;
	frappe.web_form.validate = () => {
		if (!get_verification_token()) {
			frappe.msgprint(__("Please complete the security verification before submitting the application."));
			return false;
		}
		return originalValidate ? originalValidate() : true;
	};

	async function refresh_batch_options() {
		const batch = frappe.web_form.fields_dict?.[BATCH_FIELD];
		if (!batch) {
			return;
		}
		batch.set_data([]);
		const program = frappe.web_form.fields_dict?.[PROGRAM_FIELD]?.get_value();
		if (!program) {
			return;
		}
		const requestedProgram = program;
		const response = await frappe.call({
			method: "high_school.high_school.admissions.get_public_student_batches",
			args: {program},
		});
		if (frappe.web_form.fields_dict?.[PROGRAM_FIELD]?.get_value() === requestedProgram) {
			batch.set_data(response.message || []);
		}
	}

	function set_verification_token(token) {
		const control = frappe.web_form.fields_dict?.[TOKEN_FIELD];
		if (control) {
			control.set_value(token || "");
		}
		frappe.web_form.doc[TOKEN_FIELD] = token || "";
	}

	function get_verification_token() {
		const control = frappe.web_form.fields_dict?.[TOKEN_FIELD];
		return control?.get_value?.() || frappe.web_form.doc[TOKEN_FIELD] || "";
	}

	function load_turnstile_script() {
		if (window.turnstile) {
			return Promise.resolve();
		}
		return new Promise((resolve, reject) => {
			const script = document.createElement("script");
			script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
			script.async = true;
			script.defer = true;
			script.onload = resolve;
			script.onerror = () => {
				$(".submit-btn").prop("disabled", true);
				frappe.msgprint(__("Security verification could not be loaded. Please refresh the page or contact the school."));
				reject(new Error("Cloudflare Turnstile failed to load"));
			};
			document.head.appendChild(script);
		});
	}
});
