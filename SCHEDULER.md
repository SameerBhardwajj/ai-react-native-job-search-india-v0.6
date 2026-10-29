# Automatic Job Refresh

The dashboard stores your selected websites, keywords and location in SQLite. `setup_windows.bat` creates three Windows Task Scheduler tasks:

- 10:00 AM daily
- 2:00 PM daily
- 8:00 PM daily

Each task runs `python -m rnjob.scheduler`, which reads the saved source selection and attempts a best-effort refresh from publicly accessible/searchable pages. Results are deduplicated into the local database. When you open the dashboard, it reads the latest stored data.

## Important source limitation

LinkedIn, Naukri and other job portals may use login walls, CAPTCHAs, robots controls or JavaScript rendering. The scheduler does **not** bypass these controls. A source may therefore report `blocked_or_unavailable` while other selected sources refresh normally. Use official APIs, permitted feeds, exports, public career pages or manual CSV/JSON imports where available.

To change the selection, use **Job Sources → Save selections**. The next scheduled run automatically uses the new selection.