# Security Notes — v0.6

## Network safety

- Only HTTP(S) URLs are accepted.
- Credential-bearing URLs are rejected.
- DNS-resolved addresses are checked against private, loopback, link-local, reserved, multicast and unspecified ranges.
- Redirects are not blindly followed: every redirect target is revalidated.
- Response size, redirect count and timeouts are bounded.
- Source-board candidate links are restricted to the expected source domain.

## Job-content safety

Imported job descriptions are untrusted data. Prompt-injection patterns and hidden Unicode are flagged. Untrusted JD text must not be treated as system/developer instructions.

## Dashboard safety

- Binds to `127.0.0.1` by default.
- Optional `WEB_TOKEN` authentication remains supported.
- Mutating dashboard requests reject unexpected browser origins.
- Dashboard rendering escapes untrusted job data.
- No application is submitted automatically.

## Scheduler safety

A lock file prevents overlapping refreshes. Stale locks expire after a bounded period so a crashed worker cannot permanently disable future runs.

## Privacy

The database is local SQLite. Do not expose the dashboard to the public network without adding an appropriate authenticated reverse proxy and HTTPS boundary.