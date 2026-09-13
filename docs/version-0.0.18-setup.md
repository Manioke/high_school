# High School 0.0.18 setup and verification

This corrective release fixes public admission submission, Student invoice connections, reusable multi-program batch names, balanced group assignment, and School Term fee billing.

## Install the update

Back up the site first. From the Bench directory, update the `high_school` app and run:

```bash
bench --site your-site-name backup --with-files
bench --site your-site-name migrate
bench build --app high_school
bench --site your-site-name clear-cache
bench restart
```

Migration adds the new fields, updates the public Web Form, and safely fills a missing Sales Invoice `student` link when its Customer belongs to exactly one Student.

## Required one-time configuration

### 1. Assign Programs to reusable Student Batches

Open every **Student Batch Name** and set **Program**. Batch names may now be reusable labels such as `Form 1`, but the owning Program is mandatory, for example:

| Student Batch | Program |
| --- | --- |
| Form 1 | High School |
| Grade 7 | Middle School |
| Kindergarten 1 | Kindergarten |

Applicant, enrollment, timetable, assessment, performance, and report-card batch selectors are scoped by Program. Existing `Form 1 - 2026` names can be renamed separately if desired; this release does not rename master data automatically.

### 2. Assign School Terms to Fee Schedules

Academic Term is hidden from Fee Schedule for this workflow. For every submitted Fee Schedule, set the new editable **School Term** field. A normal four-term fee structure should have four submitted schedules:

| Fee Schedule | Program | Academic Year | School Term |
| --- | --- | --- | --- |
| High School Fee - T1 | High School | 2026 | 2026-Term1 |
| High School Fee - T2 | High School | 2026 | 2026-Term2 |
| High School Fee - T3 | High School | 2026 | 2026-Term3 |
| High School Fee - T4 | High School | 2026 | 2026-Term4 |

School Terms must have correct Start Date and End Date values.

## Admission behavior

- The public form no longer exposes New/Old Student or Student ID selection.
- A literal `Today` application-date default is converted to a valid ISO date before insertion.
- Existing Students are matched from strong identity fields (including first name and date of birth), with the linked Guardian account used to disambiguate where possible.
- One unambiguous match reuses the Student. Multiple matches stop enrollment for staff review rather than guessing.
- Existing Guardian and User records are reused. A new Guardian is linked when the submitted parent email genuinely differs.
- Student Applicant `custom_student_batch_name` transfers to Program Enrollment.

## Group assignment behavior

The allocation scope is **Program + Academic Year + Student Batch**.

- One active Batch-based Student Group may have a blank Student Category. The enrollment remains blank and joins that single group.
- If the batch is later split, one blank/default group may coexist with categorized groups. Students with a category join only the matching categorized group; blank-category enrollments remain in the blank/default group.
- There may be at most one group for each category and at most one blank/default group in the same allocation scope.
- Automatic balancing chooses the eligible group with the lowest current occupancy and respects `max_strength`.
- Capacity is also enforced for a single group and for a category manually selected by staff.
- The setting remains configurable under **School MIS Settings > Automatically Balance Students Across Batch Groups**. When disabled and more than one group exists, staff must select a category.

## School Term billing behavior

Program Enrollment resolves its School Term from Enrollment Date.

- Enrollment during Term 1 creates invoices for Term 1, Term 2, Term 3, and Term 4 schedules.
- A transfer enrolled during Term 2 creates only Term 2, Term 3, and Term 4 invoices.
- Enrollment between terms starts from the next dated School Term.
- Duplicate active invoices for the same Student and Fee Schedule are skipped.
- Every created invoice explicitly stores both Student and School Term, so it appears in Student Connections and the Guardian portal.

## Verification checklist

1. Submit the public admission form and confirm no `Incorrect date value: 'Today'` error occurs.
2. Approve the applicant and use Program Enrollment Tool > Get Students > Enroll Students.
3. Confirm the Student Applicant batch reaches Program Enrollment.
4. Confirm a matching returning Student is reused and no duplicate Guardian/User is created.
5. Confirm group membership follows Program, Academic Year, Batch, Category, balance, and capacity.
6. Open the created Sales Invoice and confirm both **Student** and **School Term** are populated.
7. Open Student > Connections and confirm Sales Invoice shows a count.
8. Test an Enrollment Date in Term 1 and verify four invoices; test Term 2 and verify only Terms 2–4.
9. Confirm examination cycles now require Program and only show batches belonging to that Program.

