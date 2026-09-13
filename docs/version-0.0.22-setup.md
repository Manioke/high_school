# Version 0.0.22

This corrective core release adds a compatible whitelisted module endpoint for
School Timetable Generator course-schedule generation. Both the standard Desk
document call and older/custom callers using the full
`high_school.high_school.doctype.school_timetable_generator.school_timetable_generator.generate_schedules`
path now delegate to the same saved generator and conflict-checking logic.

After updating the app, run:

```bash
bench --site your-site migrate
bench build --app high_school
bench --site your-site clear-cache
bench restart
```

Open a saved School Timetable Generator, load courses, select instructors (and
rooms when required in School MIS Settings), then run Generate Course
Schedules.
