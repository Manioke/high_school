# Reproducible production deployment

## Decision

Use the official `frappe/frappe_docker` production Compose stack, a custom immutable image containing every required app, and Cloudflare Tunnel as the edge connection. Do not run the VS Code development container or `bench start` as a trial or production server.

Do not add Traefik initially. Cloudflare Tunnel already provides the public TLS edge and avoids opening inbound ports on the home server. Using the same Tunnel sidecar pattern in the cloud keeps the trial and customer deployments structurally identical.

## Environment model

Maintain three separate environments:

| Environment | Purpose | Data | Image |
| --- | --- | --- | --- |
| Development | Coding and debugging | Synthetic | Local development build |
| Trial | School demonstration | Synthetic sample data only | Release candidate image |
| Production | Live school operations | Real school data | The exact image digest accepted in Trial |

Each environment gets its own site, database, volumes, encryption key, administrator password, Turnstile secret, Tunnel token, email credentials, and backups. Never copy production data into Development or Trial.

## Source and image flow

1. Tag the custom app release, for example `v0.0.20`.
2. In a separate **private deployment repository**, define `apps.json` with ERPNext, Education, HRMS, Insights, and High School pinned to tested version tags or immutable commit hashes.
3. Build the official layered custom image using Frappe Framework `version-16`.
4. Tag the image with the app release and Git commit, then push it to a private container registry.
5. Deploy that image to Trial and run migrations.
6. After acceptance, promote the same image digest to Production. Do not rebuild different code for Production.

The public High School source repository must not contain database passwords, API tokens, Turnstile secrets, Tunnel tokens, SMTP credentials, `site_config.json`, backups, or real school data.

## Runtime stack

The production Compose project should contain:

- Frappe frontend (internal Nginx)
- backend workers
- WebSocket service
- scheduler
- short and long queues
- MariaDB
- Redis cache and queue
- one Cloudflare Tunnel container
- persistent site, database, and log volumes

Cloudflare Tunnel should route the public hostname to the internal Frappe frontend service. Only Cloudflare Tunnel needs outbound internet access; MariaDB and Redis must never be exposed publicly.

## Host requirements

- A supported Linux server with current Docker Engine and Docker Compose v2
- Static LAN address for the home trial server
- Reliable storage, UPS protection, and adequate memory
- Separate off-host backup destination
- Outbound access to the container registry, Git provider, SMTP server, and Cloudflare

## Required operational controls

- Daily database and site-file backups with encryption
- At least one off-host copy
- A documented and tested restore procedure
- Health checks for frontend, workers, scheduler, MariaDB, Redis, and Tunnel
- Central log retention and disk-usage alerts
- Automatic security updates for the host, with planned application upgrades
- Multi-factor authentication for administrator accounts
- No real student data in the free trial

## Turnstile per environment

The site key is public and may be built into the app. Store the secret only in **School MIS Settings → Turnstile Secret Key**.

- Trial allowed hostname: the exact trial hostname
- Production allowed hostname: the exact production hostname
- Production must not allow `localhost` or `127.0.0.1`

The hostname must also exist in the Cloudflare Turnstile widget's Hostname Management list.

## Upgrade procedure

1. Back up the database and site files.
2. Deploy the new immutable image to Trial.
3. Run the site migration and rebuild/clear caches if required.
4. Test login, enrollment, fees, attendance, assessment results, reports, scheduled jobs, email, PDF generation, and backup/restore.
5. Record the accepted image digest.
6. Deploy that same digest to Production during a maintenance window.
7. Run migration, verify workers and scheduler, and complete a smoke test.

Keep the previous image digest and pre-upgrade backup available for rollback.
