# Execution evidence

Measured on the implementation machine on 24 November 2026. Commands were run from the repository root with the local virtualenv (Python 3.13) unless noted. The dashboard figures come from the live API after the labeled demo seed and one real Pytest smoke run.

## Quality gates

| Check | Result |
| --- | --- |
| `ruff check backend scripts` | All checks passed |
| `bandit -c pyproject.toml -r backend/app -q` | Exit 0, no findings printed |
| `python scripts/scan_secrets.py` | Secret scan passed |
| `python scripts/validate_templates.py` | 14 templates valid (7 GitHub Actions, 7 Azure DevOps) |
| `python scripts/validate_docker.py` | Dockerfiles and Compose validated structurally. Docker CLI is not installed on this machine, so images were not built |
| `pytest --junitxml=reports/junit-backend.xml` | 16 passed, 0 failed, 0 errors, 0 skipped. One Starlette deprecation warning about `httpx` versus `httpx2` in `TestClient` |
| `pip-audit -r backend/requirements.txt` | No known vulnerabilities found |
| `npm test` (Vitest 2.1.9) | 1 file, 5 tests passed |
| `npm run lint` | `tsc --noEmit` clean |
| `npm run build` | Vite 5.4.21 production build succeeded (`dist/index.html`, CSS 4.29 kB, JS 205.17 kB) |
| `npm audit` | 6 remaining issues in the frontend toolchain: 3 moderate, 1 high, 2 critical, inside Vite 5.4.21, Vitest 2.1.9, esbuild, and tinypool. Upgrading Vitest 5 with Vite 8 failed npm 10.9.2 dependency resolution (`edgesOut`). Documented in `docs/security.md` |

## Live platform

API health: `{"status":"ok","service":"cicd-test-automation-platform"}` on `http://127.0.0.1:8000`.

`GET /api/analytics/summary` with the operator key:

| Field | Value |
| --- | --- |
| Total runs | 37 |
| Passed | 26 |
| Failed | 5 |
| Error | 3 |
| Running | 1 |
| Cancelled | 2 |
| Success rate | 76.5% |
| Test pass rate | 94.0% |
| Average duration | 132,446 ms |
| Demo seed runs | 36 |
| Source | database |

The 36 demo rows are labeled in the UI. Clearing **Include demo seed** on the Executions page left 1 stored run. That run is execution 37: Harbor Checkout, Pytest smoke, branch `main`, status `passed`, 2 passed tests, 0 failed, duration 184 ms, `is_demo_seed` false, triggered by `operator`.

Screenshots from that session are in `docs/screenshots/`:

- `overview.png` — dashboard totals against the live API
- `executions.png` — history including the live row and labeled demo rows
- `execution-detail.png` — execution 37 result names
- `live-runs-only.png` — demo seed hidden, one live run
- `templates.png` — GitHub and Azure templates marked valid
- `overview-mobile.png` — stacked navigation and filters at a phone-width layout

Sample exports for execution 37 are in `docs/samples/`.
