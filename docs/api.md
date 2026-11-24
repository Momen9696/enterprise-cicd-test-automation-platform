# API

Interactive OpenAPI is served at `/docs` when the API is running. Unless noted, send `X-API-Key`.

## Authentication

| Key | Role |
| --- | --- |
| `PLATFORM_API_KEY` | Read and write |
| `PLATFORM_VIEWER_KEY` | Read |

`GET /health` and the webhook routes do not use the API key. Webhooks require their signature headers.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Database connectivity |
| GET | `/api/suites` | Approved suite catalog |
| GET, POST | `/api/projects` | List or create projects |
| GET, PATCH, DELETE | `/api/projects/{id}` | Read, update, or delete one project |
| POST | `/api/projects/{id}/environments` | Add a non-secret environment map |
| GET, POST | `/api/pipelines` | List or create pipelines |
| PATCH | `/api/pipelines/{id}` | Enable, rename, or retarget the branch pattern |
| GET, POST | `/api/executions` | Filter history or start a run |
| GET | `/api/executions/{id}` | One execution |
| POST | `/api/executions/{id}/cancel` | Cancel a queued or running execution |
| GET | `/api/executions/{id}/results` | Stored test results |
| POST | `/api/executions/{id}/results` | Ingest results for `run_mode=ingest` |
| GET | `/api/analytics/summary` | Totals, success rate, average duration |
| GET | `/api/analytics/trends` | Daily passed, failed, and error counts |
| GET | `/api/analytics/projects` | Per-project stats |
| GET | `/api/analytics/failures` | Repeated failed tests |
| GET | `/api/reports/executions/{id}?format=json\|csv\|html\|md` | One execution report |
| GET | `/api/reports/aggregate?format=json\|csv\|html\|md` | Filtered aggregate report |
| GET | `/api/notifications?execution_id=` | Notification records |
| GET | `/api/providers/templates` | Template validation results |
| GET | `/api/providers/templates/{provider}/{filename}` | Template YAML |
| POST | `/api/providers/templates/validate` | Validate a template file or pasted YAML |
| GET | `/api/providers/github` | Optional GitHub Actions status |
| GET | `/api/providers/azure` | Optional Azure DevOps status |
| POST | `/api/webhooks/github` | `X-Hub-Signature-256` |
| POST | `/api/webhooks/azure` | `X-Platform-Signature` |

## Filters

Analytics, execution lists, and aggregate reports accept:

- `project_id`
- `pipeline_id`
- `branch`
- `environment`
- `status` (`queued`, `running`, `passed`, `failed`, `error`, `cancelled`)
- `date_from` and `date_to` as `YYYY-MM-DD`
- `include_demo` (`true` or `false`)

Execution lists also accept `limit` (max 200) and `offset`.

## Create an execution

```json
{
  "pipeline_id": 1,
  "branch": "main",
  "commit_sha": "abc1234",
  "trigger": "manual"
}
```

`trigger` is `manual` or `schedule`. Extra properties such as `command` return 422.

## Ingest results

```json
{
  "results": [
    {"name": "test_cart_subtotal", "suite_name": "checkout", "status": "passed", "duration_ms": 12, "message": ""}
  ],
  "duration_ms": 1200
}
```

At most 500 results are accepted. The execution must still be `queued` or `running` and the pipeline must use ingest mode.

## Summary fields

`total_runs`, `passed_runs`, `failed_runs`, `error_runs`, `running_runs`, `cancelled_runs`, `average_duration_ms`, `success_rate`, `test_pass_rate`, `demo_seed_runs`, and `source`. `source` is `database`. Success rate is passed runs divided by passed, failed, and error runs. Running and cancelled runs stay in the totals and out of that ratio. Average duration uses finished passed, failed, and error runs.
