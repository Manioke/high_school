# High School 0.0.16 setup and verification

This release repairs the Frappe Education v16 Program Enrollment Tool and adds the parent-led admission workflow.

## Upgrade

From the bench directory, install the updated app archive, then run:

```bash
bench --site your-site migrate
bench build --app high_school
bench --site your-site clear-cache
bench restart
```

Hard-refresh the browser after the build. `migrate` is required because it creates the admission, Employee, Property Setter, Role Profile, Module Profile, and Web Form configuration.

## Program Enrollment Tool

1. Select **Get Students From = Student Applicant**.
2. Select **Program** and **Academic Year**.
3. Use the standard **Get Students** button. It loads Approved Student Applicants only.
4. Review the loaded rows, then use the standard **Enroll Students** button.
5. `custom_student_batch_name` from each Student Applicant is copied to the Program Enrollment row. Category allocation follows the School MIS Settings option and Student Group capacity rules.

The obsolete **Load All Approved Applicants** button and applicant-mode **Enrollment Details** fields are no longer used.

## Parent-led public admission

After migration, every Student Applicant Web Form has:

- Parent / Guardian Name (mandatory)
- Parent / Guardian Email (mandatory)
- Student Batch (mandatory)

The existing Guardians child table is removed from the public form so a Guest cannot browse Guardian records. Student email is optional on both Student Applicant and Student. Parent email remains a validated email address because it becomes the portal login; use a complete address such as `parent@qsc.to`, not `parent@qsc`.

When an application becomes Approved, the parent receives an approval notice. When its Program Enrollment is submitted, the system:

1. creates or reuses a Website User for the parent;
2. assigns the Guardian-only role profile and empty Guardian module profile;
3. creates or reuses the Guardian record and links its `user_id`;
4. adds the Guardian to the Student's Guardian Details table;
5. sends the normal welcome/password email and an enrollment email with fee due dates, group information, and office-payment instructions.

Guardian-only users are redirected away from `/desk` and `/app` to `/edu-portal`. The fee endpoint permits a Guardian to read only Sales Invoices for linked children and supports invoices linked through either the Student field or the Student's Customer.

## Employee to Instructor

The Employee form now has **Create Instructor Automatically**. When selected, saving the Employee creates one linked Education Instructor and copies the name, department, gender, user, and active/left state. Existing Instructor-to-Employee departure synchronization remains active.

## UI corrections

- **Get Departments** appears immediately below the HOD Mapping table on School Examination Cycle.
- The legacy Student Group script no longer calls the private `set_inner_btn_group_item` API removed in Frappe v16.

## Quick test

1. Submit a public Student Applicant without a student email but with a valid parent name/email and batch.
2. Approve it and confirm an Email Queue entry is produced after the transaction commits.
3. In Program Enrollment Tool, load Approved applicants and enroll.
4. Confirm Program Enrollment has the applicant's batch, Student has the Guardian child row, Guardian has `user_id`, and the User is a Website User with Guardian access.
5. Submit a fee invoice for the Student/Customer and confirm the linked Guardian can see it in `/edu-portal` but cannot open `/desk`.
