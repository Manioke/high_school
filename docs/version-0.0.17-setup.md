# High School 0.0.17 setup and verification

This corrective release completes the parent-led admission workflow, fixes Guardian fee visibility, and hardens the public Student Applicant Web Form.

## Install the update

From the Bench directory, replace or update the `high_school` app, then run:

```bash
bench --site your-site-name migrate
bench build --app high_school
bench --site your-site-name clear-cache
bench restart
```

The migration performs these changes automatically:

- adds mandatory Parent/Guardian Name, Email, Relationship, and Student Batch fields to Student Applicant;
- makes the student email optional for Student and Student Applicant;
- adds the parent fields to every Student Applicant Web Form and removes the public Guardian master-record table;
- repairs old Student Guardian rows whose invalid relationship was recorded as `Guardian`, changing it to `Others`;
- creates the Guardian-only Role Profile and empty Module Profile if missing.

## Public admission security

Frappe already limits Web Form submissions to 10 requests per minute for each IP address. This app adds:

- a configurable hourly limit per IP address (default 20);
- a hidden bot-trap field;
- rejection of an identical student application from the same parent within 24 hours;
- optional Cloudflare Turnstile verification;
- server-side email, relation, authorization, and verification checks;
- single-use verification tokens that are never retained in Student Applicant.

To enable Turnstile:

1. Create a Turnstile widget in Cloudflare and add the public admission domain.
2. Open **School MIS Settings > Public Student Admission Security**.
3. enter the Turnstile Site Key and Secret Key.
4. Check **Require Cloudflare Turnstile** and save.
5. Test the public form in a private browser window.

If the site uses a custom Content Security Policy, permit scripts and frames from `https://challenges.cloudflare.com`.

Application controls reduce spam and automated submissions, but volumetric denial-of-service traffic must also be stopped before it reaches Frappe. Use Cloudflare proxy/WAF rate limiting (or an equivalent reverse proxy), TLS, regular updates, restricted database/Redis access, body-size limits, monitoring, and tested backups.

## Verification checklist

1. Create a Student Applicant with a valid Parent/Guardian Name, Email, Relationship, and `custom_student_batch_name`.
2. Approve it and confirm the approval email is queued.
3. In Program Enrollment Tool, use **Get Students**, then **Enroll Students**.
4. Confirm Program Enrollment `student_batch_name` matches Student Applicant `custom_student_batch_name`.
5. Confirm the Guardian and Website User are created or safely reused and Student > Guardians contains Mother, Father, or Others.
6. Confirm the enrollment email includes fees, group details, and Add to Home Screen instructions.
7. Sign in as the Guardian, open the linked child, and check Fees. Submitted invoices linked through either Sales Invoice `student` or the Student's Customer must appear.
8. For a returning applicant, confirm the existing Student is reused. The same Guardian is not duplicated; a genuinely different parent email creates or reuses another Guardian and links that Guardian to the Student.

Public returning-student details are deliberately not auto-filled from a Student ID. Exposing those records to an unauthenticated browser would allow student-data enumeration. Staff still receive Desk auto-fill. A future public self-service version should require Guardian login or an email one-time-password check before returning any existing student data.
