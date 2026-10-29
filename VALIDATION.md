# v0.6 Validation

Validation performed before packaging:

- `pytest -q`: **9 passed, 0 failed**
- Python bytecode compilation: passed
- Dashboard JavaScript syntax check with Node: passed
- FastAPI smoke test: `/api/health` returns 200
- FastAPI smoke test: source selection persists
- FastAPI smoke test: source-run history endpoint returns 200
- Private URL validation: passed
- Redirect-to-private-IP protection: passed
- JSON-LD JobPosting extraction: passed
- Source URL generation: passed
- SQLite initialization and application status/event flow: passed

## Known non-goals

- No CAPTCHA/login/robots/rate-limit bypass.
- No blind auto-apply.
- No claim that every job portal is fully scrapeable; protected or JS-only portals can return `blocked_or_unavailable` or fewer results.
- No external AI provider is called unless explicitly configured.