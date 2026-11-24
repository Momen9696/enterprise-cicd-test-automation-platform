from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Execution, Project, TestResult


def apply_filters(
    query: Select,
    *,
    project_id: int | None = None,
    pipeline_id: int | None = None,
    branch: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_demo: bool = True,
) -> Select:
    if project_id is not None:
        query = query.where(Execution.project_id == project_id)
    if pipeline_id is not None:
        query = query.where(Execution.pipeline_id == pipeline_id)
    if branch:
        query = query.where(Execution.branch == branch)
    if environment:
        query = query.where(Execution.environment_name == environment)
    if status:
        query = query.where(Execution.status == status)
    if date_from is not None:
        query = query.where(Execution.started_at >= datetime.combine(date_from, time.min))
    if date_to is not None:
        query = query.where(
            Execution.started_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    if not include_demo:
        query = query.where(Execution.is_demo_seed.is_(False))
    return query


def summary(session: Session, **filters) -> dict:
    rows = session.scalars(apply_filters(select(Execution), **filters)).all()
    total = len(rows)
    counts = {name: sum(row.status == name for row in rows) for name in ("passed", "failed", "error", "running", "cancelled", "queued")}
    finished = [row.duration_ms for row in rows if row.duration_ms is not None and row.status in {"passed", "failed", "error"}]
    average = int(sum(finished) / len(finished)) if finished else 0
    decided = counts["passed"] + counts["failed"] + counts["error"]
    success = round((counts["passed"] / decided) * 100, 1) if decided else 0.0
    test_passed = sum(row.passed_tests for row in rows)
    test_failed = sum(row.failed_tests for row in rows)
    test_total = test_passed + test_failed
    test_rate = round((test_passed / test_total) * 100, 1) if test_total else 0.0
    running = counts["running"] + counts["queued"]
    return {
        "total_runs": total,
        "passed_runs": counts["passed"],
        "failed_runs": counts["failed"],
        "error_runs": counts["error"],
        "running_runs": running,
        "cancelled_runs": counts["cancelled"],
        "average_duration_ms": average,
        "success_rate": success,
        "test_pass_rate": test_rate,
        "demo_seed_runs": sum(row.is_demo_seed for row in rows),
        "source": "database",
    }


def trends(session: Session, **filters) -> list[dict]:
    rows = session.scalars(apply_filters(select(Execution), **filters)).all()
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "failed": 0, "error": 0})
    for row in rows:
        key = row.started_at.date().isoformat()
        if row.status in buckets[key]:
            buckets[key][row.status] += 1
    return [{"date": key, **buckets[key]} for key in sorted(buckets)]


def project_stats(session: Session, **filters) -> list[dict]:
    rows = session.execute(
        apply_filters(select(Execution, Project.name), **filters).join(Project, Project.id == Execution.project_id)
    ).all()
    grouped: dict[int, dict] = {}
    for execution, name in rows:
        bucket = grouped.setdefault(
            execution.project_id,
            {"project_id": execution.project_id, "project_name": name, "runs": 0, "passed": 0, "failed": 0, "durations": []},
        )
        bucket["runs"] += 1
        if execution.status == "passed":
            bucket["passed"] += 1
        if execution.status == "failed":
            bucket["failed"] += 1
        if execution.duration_ms is not None and execution.status in {"passed", "failed", "error"}:
            bucket["durations"].append(execution.duration_ms)
    stats = []
    for bucket in grouped.values():
        decided = bucket["passed"] + bucket["failed"]
        durations = bucket.pop("durations")
        bucket["average_duration_ms"] = int(sum(durations) / len(durations)) if durations else 0
        bucket["success_rate"] = round((bucket["passed"] / decided) * 100, 1) if decided else 0.0
        stats.append(bucket)
    return sorted(stats, key=lambda item: item["project_name"])


def failure_stats(session: Session, *, limit: int = 20, **filters) -> list[dict]:
    execution_ids = session.scalars(apply_filters(select(Execution.id), **filters)).all()
    if not execution_ids:
        return []
    results = session.scalars(
        select(TestResult)
        .where(TestResult.execution_id.in_(execution_ids), TestResult.status.in_(("failed", "error")))
        .order_by(TestResult.id.desc())
    ).all()
    grouped: dict[tuple[str, str], dict] = {}
    for result in results:
        key = (result.name, result.suite_name)
        bucket = grouped.get(key)
        if bucket is None:
            execution = session.get(Execution, result.execution_id)
            project = session.get(Project, execution.project_id) if execution else None
            grouped[key] = {
                "name": result.name,
                "suite_name": result.suite_name,
                "failures": 1,
                "last_message": result.message,
                "last_seen": execution.started_at if execution else result.execution.started_at,
                "project_name": project.name if project else "",
            }
        else:
            bucket["failures"] += 1
    ordered = sorted(grouped.values(), key=lambda item: item["failures"], reverse=True)
    return ordered[:limit]

