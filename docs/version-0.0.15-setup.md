# High School 0.0.15 setup

After updating, run `bench --site <site> migrate`, `bench build --app high_school`, clear the site cache, and restart the bench processes.

## Automated program enrollment

1. In **School MIS Settings → Program Enrollment Automation**, decide whether **Randomly Assign Student Category From Batch Groups** is enabled.
2. When enabled, configure each Batch-based Student Group with Academic Year, Student Batch, Student Category and optional Max Strength. Only those categories are eligible; full groups are excluded.
3. When disabled, staff must enter Student Category on each row or use **Set Mass Batch & Category** before enrollment.
4. Open **Program Enrollment Tool**, select Program and Academic Year, then use **Load All Approved Applicants**. The tool loads every approved applicant in that scope and the normal Enroll action processes all loaded rows.
5. Submitted Program Enrollments continue to refresh every relevant main and option Student Group.

## Course timetable and option blocks

1. Name Form-specific courses consistently, for example `Form 1 English` and `Form 2 English`. A Form-labelled Batch rejects courses explicitly labelled for another Form; generic course names remain available across Forms.
2. Name option Student Groups with `Opt1`, `Opt2`, `Opt3`, or `Opt4`, for example `F5-Eco-Opt1`, `F5-Acc-Opt1`, and `F5-Commerce-Opt1`.
3. In **School Timetable Generator**, use **Load / Refresh Courses**. The detected Student Batch and Option Block are shown on each row.
4. Every row in one Batch/Option Block must have the same Periods Per Week. All Opt1 rows for a Batch are placed simultaneously. Opt2, Opt3 and Opt4 are prohibited from using the same Batch/time slot.
5. Parallel option rows need different instructors and, when rooms are mandatory, different rooms.
6. Use **View → Print Weekly Timetable**, select any date in the desired week, apply optional Batch/Group/Instructor filters, then use the report Print/PDF action.

## Exam timetable and departments

1. Set **Examination Department Parent** in School MIS Settings.
2. In School Examination Cycle, choose **Examination Preparation → Get Departments**. The button recursively loads every leaf Department below the configured parent. Remove unused rows and select the HOD User for each remaining Department before saving.
3. Use **View → Print Exam Timetable** after Assessment Plans have been generated. The report can be filtered by Student Batch or Student Group and printed or exported to PDF.

## Academic management reports

- **Departmental Analysis** compares course averages across Departments and Student Groups/streams. It includes highest, lowest, the number below the configured academic intervention threshold, and a grade for the group average when a Grading Scale is selected.
- **Average Performance per Student Batch** takes the mean of official submitted, complete Student Performance Summary overall percentages. Select a Student Group when a stream-specific result is required. The report compares each average with the School Academic Average Target in School MIS Settings.
