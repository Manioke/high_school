# Version 0.0.21 package split

Online registration is no longer part of the High School core app.

The core package retains all ordinary school operations and the manual
enrolment workflow. The optional `high_school_online_registration` app adds the
public Student Applicant form, applicant and approval emails, Turnstile,
returning-student matching, applicant enrolment, Guardian/User creation,
Guardian portal routing, and Guardian fee visibility.

## Upgrade choices

- Core-only customer: upgrade `high_school`, do not install the add-on, and
  create/import Students and Program Enrollments manually.
- Online-registration customer: upgrade `high_school`, install
  `high_school_online_registration`, run migrate, then configure Online
  Registration Settings.

Do not publish a Student Applicant Web Form on a core-only site. Existing sites
that previously stored Turnstile settings in School MIS Settings must re-enter
the Turnstile secret in Online Registration Settings after installing the
add-on; secrets are deliberately not copied by migration code.
