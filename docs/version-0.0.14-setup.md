# High School 0.0.14 setup

After updating the app, run `bench --site <site> migrate`, `bench build --app high_school`, and restart the bench processes.

## Program enrolment and Student Group capacity

1. For each main class, create a Batch-based Student Group for the correct Academic Year and Student Batch.
2. Set the Student Category accepted by that group.
3. Set Max Strength when the class has a capacity limit; leave it empty or zero for no limit.
4. When Program Enrollment is submitted with Student Batch Name but no Student Category, the app chooses only among categories configured on those groups.
5. A full category is excluded. If every eligible group is full, submission stops and identifies the affected student. A bulk Program Enrollment Tool run lists all students it could not place before creating enrolments.
6. Submitted enrolments continue to trigger Student Group membership reconciliation automatically.

## Course timetable

1. Create School Period records for every teachable period. Their From Time and To Time are the only period times used by the generator.
2. In School MIS Settings, enable **Require Rooms for Timetables** only if every scheduled lesson must have a Room.
3. Open **School Timetable Generator**, select Academic Year, School Term and optionally Student Batch, then save.
4. Use **Load / Refresh Courses**. Complete Instructor, Periods Per Week and, when required, Room.
5. Use **Generate Course Schedules**. The generator checks Student Group, Instructor and Room conflicts across the full School Term. If anything cannot be placed, no partial timetable is created and the unresolved course/week list is shown.
6. The standard Course Scheduling Tool remains available for one-course scheduling. It now uses School Period for From Time and To Time, and follows the same room setting.

## Assessments and report cards

1. Use **Bulk Assessment Plans** on the Executive MIS dashboard or High School workspace.
2. Select approved Exam Paper Requirements. The approved requirement remains authoritative for criteria, affected groups, grading scale, exam date and times. Existing plans are skipped.
3. Use **Bulk Performance Summaries & Report Cards** to generate every matching Student Performance Summary for a Program, Academic Year, School Term and Student Batch, then download one combined PDF.
4. Course grades are calculated from the Grading Scale on the contributing Assessment Plans. Plans for the same course must use one consistent scale.
5. Submitted summaries are protected. To add grades to an already-submitted summary, cancel it, regenerate the batch, review it and submit it again.

## Custom print templates

1. Duplicate **Student Performance Report Card** in Print Format Builder, customize the duplicate, and select it as **Student Report Card Print Format** in School MIS Settings.
2. Put the school logo and header in a Letter Head and select it as **Student Report Card Letter Head**.
3. Duplicate **High School Salary Slip**, remove or rearrange fields as required, and select the duplicate as **Salary Slip Print Format**.
4. A submitted Salary Slip provides **School Print → Print School Salary Slip** and uses the selected template.
