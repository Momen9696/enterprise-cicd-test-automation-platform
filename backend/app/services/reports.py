from __future__ import annotations

import csv
import html
import io
from datetime import UTC, datetime

from app.models import Execution, TestResult


def _stamp(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat() + "Z"


def execution_document(execution: Execution, results: list[TestResult]) -> dict:
    failed = [row for row in results if row.status in {"failed", "error"}]
    return {
        "execution_id": execution.id,
        "project": execution.project.name,
        "pipeline": execution.pipeline.name,
        "provider": execution.pipeline.provider,
        "classification": execution.pipeline.classification,
        "status": execution.status,
        "trigger": execution.trigger,
        "branch": execution.branch,
        "environment": execution.environment_name,
        "commit_sha": execution.commit_sha,
        "started_at": _stamp(execution.started_at),
        "finished_at": _stamp(execution.finished_at),
        "duration_ms": execution.duration_ms,
        "totals": {
            "total": execution.total_tests,
            "passed": execution.passed_tests,
            "failed": execution.failed_tests,
            "skipped": execution.skipped_tests,
        },
        "error_message": execution.error_message,
        "is_demo_seed": execution.is_demo_seed,
        "failed_tests": [
            {"name": row.name, "suite_name": row.suite_name, "message": row.message, "status": row.status}
            for row in failed
        ],
        "results": [
            {
                "name": row.name,
                "suite_name": row.suite_name,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "message": row.message,
            }
            for row in results
        ],
    }


def aggregate_document(summary: dict, projects: list[dict], failures: list[dict], executions: list[Execution]) -> dict:
    return {
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "database",
        "summary": summary,
        "projects": projects,
        "failures": [
            {
                "name": item["name"],
                "suite_name": item["suite_name"],
                "failures": item["failures"],
                "last_message": item["last_message"],
                "project_name": item["project_name"],
                "last_seen": _stamp(item["last_seen"]),
            }
            for item in failures
        ],
        "executions": [
            {
                "id": row.id,
                "project": row.project.name,
                "pipeline": row.pipeline.name,
                "status": row.status,
                "branch": row.branch,
                "environment": row.environment_name,
                "duration_ms": row.duration_ms,
                "started_at": _stamp(row.started_at),
                "is_demo_seed": row.is_demo_seed,
            }
            for row in executions
        ],
    }


def to_csv(document: dict) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if "results" in document:
        writer.writerow(["name", "suite_name", "status", "duration_ms", "message"])
        for row in document["results"]:
            writer.writerow([row["name"], row["suite_name"], row["status"], row["duration_ms"], row["message"]])
        return buffer.getvalue()
    writer.writerow(["id", "project", "pipeline", "status", "branch", "environment", "duration_ms", "started_at", "is_demo_seed"])
    for row in document["executions"]:
        writer.writerow(
            [
                row["id"],
                row["project"],
                row["pipeline"],
                row["status"],
                row["branch"],
                row["environment"],
                row["duration_ms"],
                row["started_at"],
                row["is_demo_seed"],
            ]
        )
    return buffer.getvalue()


def to_markdown(document: dict) -> str:
    if "results" in document:
        lines = [
            f"# Execution {document['execution_id']} — {document['status']}",
            "",
            f"- Project: {document['project']}",
            f"- Pipeline: {document['pipeline']}",
            f"- Branch: {document['branch']}",
            f"- Environment: {document['environment']}",
            f"- Duration (ms): {document['duration_ms']}",
            f"- Demo seed: {document['is_demo_seed']}",
            "",
            "## Failed tests",
            "",
        ]
        if not document["failed_tests"]:
            lines.append("None.")
        else:
            for row in document["failed_tests"]:
                lines.append(f"- `{row['name']}` ({row['status']}): {row['message'] or 'no message'}")
        lines.extend(["", "## Results", ""])
        for row in document["results"]:
            lines.append(f"- {row['status']}: `{row['name']}` ({row['duration_ms']} ms)")
        return "\n".join(lines) + "\n"
    summary = document["summary"]
    lines = [
        "# Aggregate execution report",
        "",
        f"- Generated: {document['generated_at']}",
        f"- Total runs: {summary['total_runs']}",
        f"- Passed: {summary['passed_runs']}",
        f"- Failed: {summary['failed_runs']}",
        f"- Running: {summary['running_runs']}",
        f"- Success rate: {summary['success_rate']}%",
        f"- Average duration (ms): {summary['average_duration_ms']}",
        "",
        "## Projects",
        "",
    ]
    for row in document["projects"]:
        lines.append(
            f"- {row['project_name']}: {row['runs']} runs, {row['success_rate']}% success"
        )
    lines.extend(["", "## Repeated failures", ""])
    if not document["failures"]:
        lines.append("None.")
    else:
        for row in document["failures"]:
            lines.append(f"- `{row['name']}` × {row['failures']} ({row['project_name']})")
    return "\n".join(lines) + "\n"


def to_html(document: dict) -> str:
    title = "Execution report" if "results" in document else "Aggregate execution report"
    body = "".join(f"<pre>{html.escape(line)}</pre>" for line in to_markdown(document).splitlines())
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;margin:2rem;color:#1c2430}"
        "pre{white-space:pre-wrap;font-family:ui-monospace,monospace}</style>"
        f"</head><body><h1>{html.escape(title)}</h1>{body}</body></html>"
    )
