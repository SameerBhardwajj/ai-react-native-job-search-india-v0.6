# Multi-source job search

The v0.5 dashboard includes a **multi-select Job Sources** screen. Select any combination of LinkedIn, Naukri, Indeed India, Foundit, Instahyre, Hirist, Cutshort, Wellfound, company career pages and manual/CSV/JSON imports.

Important: source selection is an orchestration layer. It does not bypass login walls, CAPTCHAs, robots restrictions or site protections. A source adapter must use a permitted/public endpoint, user-provided export, API, feed or manual import. The UI keeps the selected source IDs in browser storage and the backend exposes `/api/sources` so real adapters can be attached cleanly.