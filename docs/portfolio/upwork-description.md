# Upwork portfolio description

**CI/CD Test Automation Platform (FastAPI, React, Pytest, Robot Framework, Playwright)**

I designed and built a local platform for managing automated test pipelines. Teams can register projects and environments, configure Pytest, Robot Framework, and Playwright pipelines, and separate smoke, regression, pull request, and scheduled runs. GitHub Actions and Azure DevOps YAML templates are included and validated. External jobs can post JUnit results, and signed webhooks can open a run when a pull request matches a pipeline.

The execution service only runs catalog suites. It does not accept shell commands or arbitrary paths. API keys split read-only and operator access. Webhook signatures are required. Secrets are kept in environment variables and stripped from child processes and logs.

The React dashboard shows stored totals, pass and fail trends, project stats, recent runs, and failure history, with filters for project, pipeline, branch, environment, status, and date. Demo rows are labeled and can be hidden. Reports export to HTML, CSV, and Markdown.

The stack is Python, FastAPI, SQLite, React, TypeScript, Vite, Pytest, Robot Framework, Playwright, Docker Compose, GitHub Actions, and Azure DevOps YAML. The verification record is in `docs/execution-evidence.md`.

**Skills:** Python, FastAPI, SQLite, React, TypeScript, Pytest, Robot Framework, Playwright, GitHub Actions, Azure DevOps, Docker, CI/CD, test reporting
