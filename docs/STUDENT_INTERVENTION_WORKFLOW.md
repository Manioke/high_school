# Automated Student Intervention Workflow

## Ownership

The **Plan Owner** is the enabled Frappe User linked to the Instructor scheduled for the plan's Course and Student Group. The owner diagnoses the issue, records concrete actions, assigns any action items, and starts monitoring. The HOD, counselor, Education Managers, and Academics Users are escalation and oversight roles; they are not substituted for a clearly mapped course instructor.

If a Course Schedule has no single Instructor/User mapping, School MIS Settings' **Default Intervention Owner** is used and the mapping problem is included in the plan's trigger reason. Correcting the mapping is preferable to relying on this fallback.

## Academic automation

1. A submitted, complete Student Performance Summary is the authoritative trigger.
2. The student's overall percentage must be below **Academic Intervention Score Threshold**.
3. The system evaluates each completed Course Result. It creates one plan per weak course when the course result is below the threshold or meets the configured statistical-outlier rule. Two weak courses therefore create two course-specific plans.
4. The scheduled course Instructor becomes the Plan Owner and receives an in-app notification, a ToDo, and—when enabled—an email.
5. The instructor records the root cause and concrete actions, then moves the plan through Action Planned, In Progress, and Monitoring.
6. The next submitted official Student Performance Summary for that student is the outcome evidence. It is compared with the immediately preceding School Term in the same Academic Year.
7. A positive overall percentage-point change closes the preceding term's plans as successful. No improvement automatically escalates them.
8. A current plan is also escalated when the overall result remains below the threshold for **Consecutive Low Performance Terms for Escalation**.

Term 1 normally establishes the baseline. Term 2 compares with Term 1, Term 3 with Term 2, and Term 4 with Term 3.

## Course-attendance automation

1. Only submitted Student Attendance linked to a Course Schedule is evaluated.
2. The system counts the latest consecutive Absent records for the same student, course, Student Group, and Instructor.
3. At **Consecutive Course Absences to Create Plan**, it creates one course-specific attendance plan and assigns the scheduled Instructor.
4. When the owner first moves the plan to Action Planned, In Progress, Monitoring, or Ready for Review, the system records **Action Monitoring Started On**.
5. Further submitted absences for that exact course responsibility are counted from that point.
6. At **Additional Course Absences to Escalate**, the plan is automatically escalated.

## Escalation and email

Automatic escalation notifies the configured School Counselor and School Principal, plus all enabled users with Education Manager or Academics User. The email contains the student, course, Student Group, trigger evidence, escalation reason, recorded actions, and a link to the plan. Enable or disable these emails with **Send Automatic Intervention Emails**.

## Dates

The old plan-level Review Date is retained only as a hidden legacy field. Academic success is determined by the next official summary, and attendance escalation is determined by new attendance evidence. Due Date remains required on individual action rows because it is an accountability deadline for the staff member assigned to that specific task; it does not determine whether the student improved.

## Required setup

- Every Course Schedule must have one Instructor for its Course and Student Group.
- Every Instructor must resolve to an enabled User, either directly (where supported) or through Instructor → Employee → User ID.
- Configure School Counselor User and, optionally, School Principal User and Default Intervention Owner.
- Give the working staff the appropriate Instructor, Academics User, or Education Manager roles.
- Keep the daily scheduler enabled so imported/backfilled records are rechecked.
