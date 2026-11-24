# Upwork case study

## CI/CD test automation platform

I built a local platform that gives a team one place to configure test pipelines, run an approved set of suites, and read the history. The backend is FastAPI and SQLite. The dashboard is React and TypeScript. The runner supports Pytest, Robot Framework, and Playwright through fixed adapters. GitHub Actions and Azure DevOps are represented by working YAML templates and optional read-only API status checks.

The constraint I treated as part of the design: the HTTP API must not become a shell. Callers choose a catalog suite, a classification, and a branch pattern. They cannot submit a command, a script, or a path. Child processes are started with `shell` disabled, an interpreter module allow-list, a timeout, and an environment that does not include the platform keys or provider tokens. Webhooks are HMAC-checked before the JSON is trusted. A repeated delivery id does not create a second run.

The dashboard reads the same database the API writes. Demo history is seeded so the screens are usable on a fresh checkout, and every seeded row is marked. A filter removes that seed. Live Pytest and Robot runs from the test suite show up beside it. Reports export to HTML, CSV, and Markdown. Failure analysis groups stored failed tests instead of scraping logs by hand.

The repository also includes the platform's own GitHub Actions workflow: Ruff, Bandit, a secret scan, pip-audit, backend tests, frontend tests, a production build, and template validation. Sample Azure pipelines are ready to copy, with secrets left in Azure variable groups rather than in the YAML.

This is a single-node local system. It does not pretend to be a hosted multi-tenant CI product. That limit is documented, including the static API keys and the decision to keep executable suites inside the repository.

The measured test, lint, and scan results are in `docs/execution-evidence.md`. Screenshots in `docs/screenshots/` were taken from the running dashboard.
