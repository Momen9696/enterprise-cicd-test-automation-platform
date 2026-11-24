# Security

This is a local demonstration platform with a deliberate trust boundary. It is not a multi-tenant production control plane.

## Controls that are implemented

- Operator and viewer keys are compared with `hmac.compare_digest`. Viewer keys can read. Mutations return 403.
- Webhooks fail closed. A missing or incorrect HMAC returns 401. The signature is computed on the raw body before JSON parsing. Bodies over 256 KB return 413.
- Duplicate delivery ids are stored and ignored.
- Projects, pipelines, executions, environments, branches, and test names are validated. Unknown fields are rejected, including any `command` field.
- Environment variables whose names contain `SECRET`, `TOKEN`, `PASSWORD`, `CREDENTIAL`, `API_KEY`, or `PAT` are rejected. The platform is not a secret store. Put CI credentials in GitHub secrets or Azure secret variables.
- The runner allows three modules: `pytest`, `robot`, and `app.services.playwright_suite`. The command starts with the current interpreter, uses `shell=False`, and a timeout. The child environment does not receive `PLATFORM_API_KEY`, `WEBHOOK_SECRET`, `GITHUB_TOKEN`, or `AZURE_PAT`.
- Suite directories must resolve inside `sample-suites` and match the catalog. The Playwright module exits 2 for any other directory, and scenario fixtures must be HTML files inside that suite.
- Failure messages and log lines pass through a redactor that replaces `token=...` style assignments.
- Notification records store a status summary, not the downstream response body.
- Provider status responses include a count and a configuration flag, not the token.
- The repository CI runs Ruff, Bandit, a secret pattern scan, and `pip-audit`.
- The Docker backend image runs as a non-root user and keeps the database on a volume.

## Limitations

- API keys are static environment values. There is no SSO, rotation service, or per-user audit identity beyond the optional `actor` query string.
- `/docs` is open on the bind address. The documented process binds the API to `127.0.0.1`. Do not publish port 8000 to the internet with the sample keys.
- SQLite has no row-level tenant isolation.
- A local adapter can execute the shipped suites, which are code in this repository. That is an approved configuration, not an anonymous remote shell. Do not point `SUITE_ROOT` at an untrusted tree.
- Cancel sends `terminate` to a process the platform started. A suite that ignores termination can run until the timeout, which defaults to 120 seconds and cannot be set above 900.
- Webhook matching trusts the signed JSON. Anyone who knows `WEBHOOK_SECRET` can create executions for matching pipelines.
- GitHub Action versions in the examples use major tags such as `@v4`, not immutable commit SHAs. Pin them when you copy the templates into a production repository.
- Dependency scanning covers the pinned Python requirements. It does not scan the optional Playwright package unless that file is installed.
- The demo seed is synthetic operational history. It is labeled and can be excluded with `include_demo=false`. It is not evidence of a production pipeline.
- The secret scan looks for known token prefixes and private-key headers. It will not catch every credential shape. `.env` is gitignored.
- `pip-audit` against `backend/requirements.txt` reports no known vulnerabilities after FastAPI 0.165.0, Starlette 1.10.0, and Pytest 9.0.3. Bandit reports no findings. The subprocess and XML-writer lines are marked `# nosec` because the runner allow-list and `defusedxml` parsing are the controls, and Bandit cannot see that from the call alone.
- `npm audit` on the dashboard still reports vulnerabilities in Vite 5.4.21 and Vitest 2.1.9 (`esbuild` dev-server request exposure, a Vite path traversal, and a Vitest/Tinypool advisory). React Router is on 7.18.6, which is outside the affected 7.17 range. Vite 8 and Vitest 5 are published, but npm 10.9.2 crashes while resolving Vitest 5 (`edgesOut`). Those findings are in the frontend toolchain, not in the API process. Do not expose the Vite dev server beyond localhost.

## Placeholder values

`.env.example` contains `local-operator-key`, `local-viewer-key`, and `local-webhook-secret`. Replace them before any shared deployment. They are intentionally not high-entropy production secrets.
