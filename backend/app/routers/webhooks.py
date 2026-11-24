from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import SessionLocal
from app.models import Execution, Pipeline, Project, WebhookDelivery, utcnow
from app.security import verify_signature
from app.services.engine import branch_matches, schedule_execution

router = APIRouter()


def _repo_matches(project: Project, full_name: str) -> bool:
    if not project.repository_url:
        return False
    return project.repository_url.rstrip("/").endswith(full_name.strip("/"))


def _create_execution(session: Session, pipeline: Pipeline, *, trigger: str, branch: str, sha: str | None, pr: int | None) -> Execution:
    execution = Execution(
        project_id=pipeline.project_id,
        pipeline_id=pipeline.id,
        environment_name=pipeline.environment.name if pipeline.environment else "dev",
        status="queued",
        trigger=trigger,
        branch=branch,
        commit_sha=sha,
        pull_request_number=pr,
        triggered_by="webhook",
        is_demo_seed=False,
        started_at=utcnow(),
    )
    session.add(execution)
    session.flush()
    return execution


@router.post("/webhooks/github")
async def github_webhook(request: Request) -> dict:
    return await _handle(request, provider="github", signature_header="X-Hub-Signature-256", delivery_header="X-GitHub-Delivery")


@router.post("/webhooks/azure")
async def azure_webhook(request: Request) -> dict:
    return await _handle(request, provider="azure", signature_header="X-Platform-Signature", delivery_header="X-Azure-Delivery")


async def _handle(request: Request, *, provider: str, signature_header: str, delivery_header: str) -> dict:
    settings = get_settings()
    body = await request.body()
    if len(body) > settings.max_webhook_bytes:
        raise HTTPException(status_code=413, detail="Payload too large")
    if not verify_signature(body, request.headers.get(signature_header), settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")
    delivery_id = request.headers.get(delivery_header, "")[:120]
    with SessionLocal() as session:
        if delivery_id:
            existing = session.scalar(
                select(WebhookDelivery).where(
                    WebhookDelivery.provider == provider,
                    WebhookDelivery.delivery_id == delivery_id,
                )
            )
            if existing:
                return {"accepted": True, "duplicate": True, "executions": []}
            session.add(WebhookDelivery(provider=provider, delivery_id=delivery_id))
        executions = _match(session, provider, payload)
        session.commit()
        ids = [item.id for item in executions]
    for execution_id in ids:
        schedule_execution(execution_id)
    return {"accepted": True, "duplicate": False, "executions": ids}


def _match(session: Session, provider: str, payload: dict) -> list[Execution]:
    event = str(payload.get("event") or payload.get("action") or "")
    repository = payload.get("repository") or {}
    full_name = ""
    if isinstance(repository, dict):
        full_name = str(repository.get("full_name") or repository.get("name") or "")
    pull = payload.get("pull_request") or payload.get("pullRequest") or {}
    branch = "main"
    sha = None
    pr_number = None
    trigger = "push"
    classification = {"smoke", "regression"}
    if isinstance(pull, dict) and pull:
        trigger = "pull_request"
        classification = {"pr_validation"}
        head = pull.get("head") or {}
        if isinstance(head, dict):
            branch = str(head.get("ref") or head.get("name") or "main")
            sha = head.get("sha")
        pr_number = pull.get("number") or pull.get("pullRequestId")
    else:
        ref = str(payload.get("ref") or "")
        if ref.startswith("refs/heads/"):
            branch = ref.removeprefix("refs/heads/")
        sha = payload.get("after")
    if not isinstance(branch, str):
        branch = "main"
    if len(branch) > 200 or any(char in branch for char in " ;|&$`"):
        return []
    if sha is not None:
        sha = str(sha)
        if len(sha) > 40:
            sha = sha[:40]
    provider_name = "github_actions" if provider == "github" else "azure_devops"
    pipelines = session.scalars(
        select(Pipeline)
        .options(selectinload(Pipeline.project), selectinload(Pipeline.environment))
        .where(Pipeline.enabled.is_(True), Pipeline.provider == provider_name)
    ).all()
    created: list[Execution] = []
    for pipeline in pipelines:
        if pipeline.classification not in classification:
            continue
        if full_name and not _repo_matches(pipeline.project, full_name):
            continue
        if not branch_matches(pipeline.branch_pattern, branch):
            continue
        created.append(
            _create_execution(
                session,
                pipeline,
                trigger=trigger,
                branch=branch,
                sha=sha if isinstance(sha, str) else None,
                pr=pr_number if isinstance(pr_number, int) else None,
            )
        )
        if len(created) >= 10:
            break
    _ = event
    return created
