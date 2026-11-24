from __future__ import annotations

import logging

import httpx

from app.config import get_settings
from app.database import SessionLocal
from app.models import Execution, NotificationRecord, utcnow
from app.security import redact

logger = logging.getLogger("platform.notifications")


def _record(session, execution_id: int, channel: str, status: str, summary: str) -> None:
    session.add(
        NotificationRecord(
            execution_id=execution_id,
            channel=channel,
            status=status,
            summary=redact(summary)[:500],
            created_at=utcnow(),
        )
    )


def dispatch_notifications(execution_id: int) -> None:
    settings = get_settings()
    with SessionLocal() as session:
        execution = session.get(Execution, execution_id)
        if execution is None:
            return
        summary = (
            f"Execution {execution.id} {execution.status} "
            f"on {execution.branch} ({execution.environment_name})"
        )
        logger.info("notification channel=log execution_id=%s status=%s", execution.id, execution.status)
        _record(session, execution.id, "log", "sent", summary)
        if not settings.notify_webhook_url:
            _record(session, execution.id, "webhook", "skipped", "Webhook channel not configured")
            session.commit()
            return
        payload = {
            "execution_id": execution.id,
            "status": execution.status,
            "project_id": execution.project_id,
            "pipeline_id": execution.pipeline_id,
            "branch": execution.branch,
            "environment": execution.environment_name,
        }
        try:
            response = httpx.post(settings.notify_webhook_url, json=payload, timeout=5.0)
            state = "sent" if response.status_code < 400 else "failed"
            _record(
                session,
                execution.id,
                "webhook",
                state,
                f"Webhook delivery status {response.status_code}",
            )
        except httpx.HTTPError:
            _record(session, execution.id, "webhook", "failed", "Webhook delivery failed")
        session.commit()
