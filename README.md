### High School Core MIS

A custom app that extends Education with manual Program Enrollment, balanced
class allocation, timetables, attendance, assessment operations, executive MIS,
board reporting, student fee monitoring, and ERPNext/Frappe HR financial
oversight.

Public applications, applicant emails, Cloudflare Turnstile, automatic
applicant enrolment, and automatic Guardian portal provisioning are delivered
separately in the optional `high_school_online_registration` app.

### Base-package enrolment workflow

1. Create or import the Student and any required User/Guardian records.
2. Create a Program Enrollment manually.
3. Select Program, Academic Year, Student Batch, and—when automatic balancing
   is disabled—Student Category.
4. Submit it. Core fee creation, Student field synchronization, balanced class
   allocation, and Student Group refresh continue to run normally.

See [School Finance Setup and Demo Guide](docs/SCHOOL_FINANCE_DEMO.md) for the required Company, Cost Center, Account, Budget, purchase, fee, and payroll configuration.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app high_school
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/high_school
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
