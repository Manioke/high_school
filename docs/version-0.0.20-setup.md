# High School 0.0.20

This final report correction changes **Average Performance per Student Batch** as follows:

- With no Student Batch selected, the report shows one aggregate row per batch.
- With a Student Batch selected, the report shows every associated Student Group as a separate row.
- A group without a completed official Student Performance Summary is retained and marked **No Data**.
- The Student Group filter is restricted by Program, Academic Year, and Student Batch.

It also completes the existing Cloudflare Turnstile integration:

- site key `0x4AAAAAAEyC-Z8GCHiJAmgp` is installed as the default;
- browser tokens are labelled with the stable `student_admission` action;
- the server requires successful Siteverify validation, that exact action, and an approved hostname;
- the secret remains in the Password field in School MIS Settings and is never committed to source control.

After updating the app, run:

```bash
bench --site your-site-name migrate
bench build --app high_school
bench --site your-site-name clear-cache
bench restart
```

Hard-refresh the report page after the build completes.

For local testing, set **Turnstile Allowed Hostnames** to `development.localhost,localhost,127.0.0.1`. For production, replace these with the exact public hostname configured on the existing Cloudflare widget.
