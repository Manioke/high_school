# High School 0.0.19 setup and verification

This release fixes the public admission batch filter, preserves Student Batch when using the single-applicant Enroll action, adds an application receipt email, and reorganizes school navigation.

## Upgrade

From the bench directory, replace or update the app and run:

```bash
bench --site your-site-name migrate
bench build --app high_school
bench --site your-site-name clear-cache
bench restart
```

After rebuilding, hard-refresh the browser so the revised Web Form JavaScript is loaded.

## Public admission security

The captcha integration is **Cloudflare Turnstile**, not Google reCAPTCHA. It remains optional because a site key and secret key are required for the school's domain.

To display it, open **School MIS Settings**, enter the Turnstile site key and secret key, and enable **Public Admission Turnstile**. When enabled but not correctly configured, public submission is blocked instead of silently bypassing verification.

Even when Turnstile is disabled, the app still applies:

- Frappe's Web Form request rate limiting;
- an additional per-IP hourly admission limit;
- a hidden honeypot field; and
- duplicate-application detection over a 24-hour window.

## Verification checklist

1. Open the public Student Applicant form in a private browser window.
2. Before selecting Program, open Student Batch and confirm that it returns no choices.
3. Select **Middle School** and confirm that only batches whose **Student Batch Name → Program** is Middle School appear.
4. Submit an application and confirm that the parent receives an **Application received** email containing the application ID, student, program, academic year, batch, and date.
5. Approve the applicant, use the built-in **Enroll** action, and confirm that the draft Program Enrollment contains the same Student Batch.
6. Run migrate and confirm that users with the Instructor role can see both the Education and High School workspaces.
7. Open High School and confirm the Student Management, Scheduling and Attendance, Assessment and Performance, Automation Tools, Reports, School Finance, and Administration sections.
8. On Executive Dashboard, use **Average Performance by Batch** beside **Open Academic Plans** and confirm that the report opens with Academic Year and School Term carried across.

If an email is not delivered immediately, inspect **Email Queue**. The message is queued after the application database transaction commits.
