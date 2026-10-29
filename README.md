# AI React Native Job Search India — v0.6.1

A local-first job intelligence dashboard focused on **React Native roles in the Indian market**.

## v0.6.1 highlights

- Visual dashboard; normal use does not require CLI commands.
- Persistent multi-select job sources: LinkedIn, Naukri, Indeed India, Foundit, Instahyre, Hirist, Cutshort, Wellfound and company-career discovery.
- Saved keywords + location are reused by the Windows scheduler.
- Windows Task Scheduler refreshes at **10:00 AM, 2:00 PM and 8:00 PM** local Windows time.
- Source-specific public-page extraction with JSON-LD `JobPosting` support and safe anchor fallback.
- Source health/history stored in SQLite.
- URL deduplication and refresh-aware upserts.
- React Native-specific matching, salary, experience, notice-period and location checks.
- ATS / AI modules from earlier versions remain available.
- Human-in-the-loop: **never auto-submits applications**.
- Redirect-aware SSRF protection validates every redirect target.
- Localhost/private/reserved/link-local/multicast/credential-bearing URLs blocked.
- Prompt-injection and hidden-Unicode detection retained for imported job content.
- Same-origin mutation guard for dashboard writes.
- Refresh lock prevents overlapping scheduled runs.
- SQLite foreign keys and indexes enabled.

## Windows setup

1. Extract the ZIP.
2. Double-click `setup_windows.bat` once.
3. Select your sources and search configuration in **Job Sources**.
4. Double-click `start_dashboard.bat` whenever you want to use the dashboard.

The scheduled worker does not require the dashboard to be open.

## Important source limitation

This project uses only public/permitted access patterns. It does **not** bypass CAPTCHA, authentication, robots restrictions, rate limits, paywalls or other access controls. A source can report `blocked_or_unavailable`; that is treated as a normal source-health state rather than bypassed.

For sources that expose structured `JobPosting` data, v0.6.1 extracts that data first. Otherwise it falls back to public job links and safely fetches candidate pages. JavaScript-only portals may still expose fewer results because this project does not use browser automation to bypass access controls.

## Scheduler

`setup_windows.bat` creates:

- `RNJobSearch - 10AM`
- `RNJobSearch - 2PM`
- `RNJobSearch - 8PM`

The tasks execute `scheduled_refresh.bat`, which changes to the project directory before starting Python. This avoids the common Task Scheduler working-directory failure.

## Security

See `SECURITY.md` for the threat model and `VALIDATION.md` for the v0.6.1 verification results.