from __future__ import annotations

import threading
import time

from app.catalog import get_suite
from app.config import get_settings
from app.database import SessionLocal
from app.models import Execution, TestResult, utcnow
from app.security import redact
from app.services.adapters import command_for
from app.services.junit import parse_junit
from app.services.notifications import dispatch_notifications
from app.services.process import run_command, terminate_process

_threads: set[threading.Thread] = set()


def branch_matches(pattern: str, branch: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("/*"):
        prefix = pattern[:-1]
        return branch.startswith(prefix) and ".." not in branch
    return pattern == branch


def _counts(cases) -> tuple[int, int, int, int]:
    passed = sum(case.status == "passed" for case in cases)
    failed = sum(case.status in {"failed", "error"} for case in cases)
    skipped = sum(case.status == "skipped" for case in cases)
    return len(cases), passed, failed, skipped


def _status_for(returncode: int, cases, timed_out: bool, cancelled: bool) -> str:
    if cancelled:
        return "cancelled"
    if timed_out:
        return "error"
    if any(case.status in {"failed", "error"} for case in cases):
        return "failed"
    if cases and returncode == 0:
        return "passed"
    if not cases:
        return "error"
    return "error"


def execute(execution_id: int) -> None:
    settings = get_settings()
    with SessionLocal() as session:
        execution = session.get(Execution, execution_id)
        if execution is None or execution.status in {"cancelled", "passed", "failed", "error"}:
            return
        pipeline = execution.pipeline
        execution.status = "running"
        execution.started_at = utcnow()
        session.commit()
        suite_id = pipeline.suite_id
        classification = pipeline.classification
        run_mode = pipeline.run_mode

    if run_mode != "local":
        return

    artifact_dir = settings.artifact_root / str(execution_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    junit_path = artifact_dir / "junit.xml"
    timed_out = False
    cancelled = False
    stderr = ""
    returncode = 1
    clock = time.perf_counter()
    try:
        spec = get_suite(suite_id)
        command, suite_dir = command_for(suite_id, classification, junit_path)
        if spec.adapter not in {"pytest", "robot", "playwright"}:
            raise RuntimeError("Adapter is not approved")
        returncode, timed_out, stderr = run_command(execution_id, command, suite_dir)
    except Exception as exc:  # noqa: BLE001
        stderr = redact(str(exc))
        returncode = 1
    cases = parse_junit(junit_path) if junit_path.is_file() else []
    with SessionLocal() as session:
        execution = session.get(Execution, execution_id)
        if execution is None:
            return
        if execution.status == "cancelled":
            cancelled = True
        status = _status_for(returncode, cases, timed_out, cancelled)
        total, passed, failed, skipped = _counts(cases)
        if not cancelled:
            execution.status = status
        execution.finished_at = utcnow()
        execution.duration_ms = max(1, int((time.perf_counter() - clock) * 1000))
        execution.total_tests = total
        execution.passed_tests = passed
        execution.failed_tests = failed
        execution.skipped_tests = skipped
        if status == "error":
            if timed_out:
                execution.error_message = "Execution timed out"
            elif not cases:
                execution.error_message = redact(stderr or "No tests were collected")[:500]
            else:
                execution.error_message = redact(stderr)[:500] or "Execution error"
        elif status == "failed":
            execution.error_message = None
        for case in cases:
            session.add(
                TestResult(
                    execution_id=execution.id,
                    suite_name=case.suite_name,
                    name=case.name[:200],
                    status=case.status,
                    duration_ms=case.duration_ms,
                    message=case.message,
                    classification=classification,
                )
            )
        session.commit()
    dispatch_notifications(execution_id)


def schedule_execution(execution_id: int) -> None:
    settings = get_settings()
    if settings.execution_inline:
        execute(execution_id)
        return
    thread = threading.Thread(target=execute, args=(execution_id,), daemon=True)
    _threads.add(thread)
    thread.start()


def request_cancel(execution_id: int) -> str:
    with SessionLocal() as session:
        execution = session.get(Execution, execution_id)
        if execution is None:
            return "missing"
        if execution.status not in {"queued", "running"}:
            return "finished"
        execution.status = "cancelled"
        execution.finished_at = utcnow()
        if execution.started_at and execution.duration_ms is None:
            execution.duration_ms = max(
                0, int((execution.finished_at - execution.started_at).total_seconds() * 1000)
            )
        session.commit()
    terminate_process(execution_id)
    dispatch_notifications(execution_id)
    return "cancelled"
