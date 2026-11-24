# Pipeline integration

The files in `pipelines/github` and `pipelines/azure` are examples for a repository that already has tests. They are not the workflows that run this platform's own CI. This repository's CI is `.github/workflows/ci.yml`. Copy a template into the other repository and point the publish step at an execution created here.

`python scripts/validate_templates.py` parses every template and checks:

- GitHub workflows have a trigger, at least one job, and steps that use `run` or `uses`.
- Azure pipelines have `trigger`, `pr`, or `schedules`, plus steps or stages and a pool.
- The text does not contain `curl | sh`, `wget | bash`, `chmod 777`, or `eval(`.

## Required configuration

Create an ingest-mode pipeline in the platform and start an execution, or let a signed webhook create one. Then set these values in the external CI system. Do not commit them.

| Name | GitHub | Azure | Purpose |
| --- | --- | --- | --- |
| Platform URL | variable `TEST_PLATFORM_URL` | variable `TEST_PLATFORM_URL` | API origin, no trailing path |
| API key | secret `TEST_PLATFORM_API_KEY` | secret variable `TEST_PLATFORM_API_KEY` | Operator key |
| Execution id | variable `TEST_PLATFORM_EXECUTION_ID` | variable `TEST_PLATFORM_EXECUTION_ID` | Ingest target |

The publish script reads `JUNIT_PATH` and posts JSON to `/api/executions/{id}/results`. It prints the HTTP status and does not print the key.

## Templates

| File | When it runs | Test command |
| --- | --- | --- |
| `pytest.yml` | push to `main` and pull requests | `pytest` with JUnit |
| `robot-framework.yml` | push to `main` and pull requests | `robot` with xUnit |
| `playwright.yml` | push to `main` and pull requests | catalog Playwright runner |
| `smoke.yml` | push to `main` | `pytest -m smoke` |
| `regression.yml` | push to `main` | `pytest -m regression` |
| `pull-request-validation.yml` | pull requests only | `pytest -m smoke` |
| `scheduled.yml` | weekdays at 06:00 UTC, plus manual dispatch | full `pytest` |

Azure files use the same names. Scheduled Azure pipelines set `trigger: none`, `pr: none`, and a weekday `schedules` block. Pull request Azure pipelines set `trigger: none` and a `pr` block.

## Webhooks

GitHub delivery uses `X-Hub-Signature-256` with `WEBHOOK_SECRET` and HMAC-SHA256 of the raw body. Azure-style delivery uses the same HMAC in `X-Platform-Signature`. Send a stable `X-GitHub-Delivery` or `X-Azure-Delivery` value. A repeat of that id is acknowledged and does not create another execution.

A GitHub `pull_request` payload creates executions for enabled `github_actions` pipelines whose classification is `pr_validation`, whose project repository URL ends with `repository.full_name`, and whose branch pattern matches the head ref. Push events match `smoke` and `regression` pipelines. Azure payloads follow the same rules for `azure_devops` pipelines.

Example pull request body:

```json
{
  "action": "opened",
  "repository": {"full_name": "example/harbor-checkout"},
  "pull_request": {"number": 18, "head": {"ref": "feature/tax-rounding", "sha": "abc1234def"}}
}
```

## Local runs

Pipelines with `run_mode=local` do not need GitHub or Azure. The dashboard Run button, or `POST /api/executions`, executes the catalog suite on this machine. `manual` is accepted for every classification. `schedule` is accepted only when the pipeline classification is `scheduled`.
