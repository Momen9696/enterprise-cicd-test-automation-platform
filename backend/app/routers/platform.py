from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.catalog import CATALOG
from app.database import get_db
from app.models import Environment, Execution, NotificationRecord, Pipeline, Project, TestResult, utcnow
from app.schemas import (
    EnvironmentCreate,
    EnvironmentOut,
    ExecutionCreate,
    ExecutionOut,
    ExecutionPage,
    FailureStat,
    IngestCreate,
    NotificationOut,
    PipelineCreate,
    PipelineOut,
    PipelineUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectStat,
    ProjectUpdate,
    ProviderStatus,
    SuiteOut,
    SummaryOut,
    TemplateOut,
    TemplateValidateRequest,
    TestResultOut,
    TrendPoint,
    adapter_for,
)
from app.security import get_role, redact, require_operator
from app.services.analytics import failure_stats, project_stats, summary, trends
from app.services.engine import branch_matches, request_cancel, schedule_execution
from app.services.providers import azure_status, github_status
from app.services.reports import aggregate_document, execution_document, to_csv, to_html, to_markdown
from app.services.templates import list_templates, read_template, validate_submission

router = APIRouter()


def _project_or_404(session: Session, project_id: int) -> Project:
    project = session.scalar(
        select(Project).options(selectinload(Project.environments)).where(Project.id == project_id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _pipeline_or_404(session: Session, pipeline_id: int) -> Pipeline:
    pipeline = session.scalar(
        select(Pipeline)
        .options(selectinload(Pipeline.project), selectinload(Pipeline.environment))
        .where(Pipeline.id == pipeline_id)
    )
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


def _execution_or_404(session: Session, execution_id: int) -> Execution:
    execution = session.scalar(
        select(Execution)
        .options(
            selectinload(Execution.project),
            selectinload(Execution.pipeline),
            selectinload(Execution.results),
        )
        .where(Execution.id == execution_id)
    )
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


def execution_out(execution: Execution) -> ExecutionOut:
    return ExecutionOut(
        id=execution.id,
        project_id=execution.project_id,
        project_name=execution.project.name,
        pipeline_id=execution.pipeline_id,
        pipeline_name=execution.pipeline.name,
        environment_name=execution.environment_name,
        status=execution.status,
        trigger=execution.trigger,
        branch=execution.branch,
        commit_sha=execution.commit_sha,
        pull_request_number=execution.pull_request_number,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        duration_ms=execution.duration_ms,
        total_tests=execution.total_tests,
        passed_tests=execution.passed_tests,
        failed_tests=execution.failed_tests,
        skipped_tests=execution.skipped_tests,
        error_message=execution.error_message,
        triggered_by=execution.triggered_by,
        is_demo_seed=execution.is_demo_seed,
        provider=execution.pipeline.provider,
        classification=execution.pipeline.classification,
    )


def pipeline_out(session: Session, pipeline: Pipeline) -> PipelineOut:
    latest = session.scalar(
        select(Execution).where(Execution.pipeline_id == pipeline.id).order_by(Execution.id.desc()).limit(1)
    )
    return PipelineOut(
        id=pipeline.id,
        project_id=pipeline.project_id,
        project_name=pipeline.project.name,
        environment_id=pipeline.environment_id,
        environment_name=pipeline.environment.name if pipeline.environment else None,
        name=pipeline.name,
        provider=pipeline.provider,
        template_key=pipeline.template_key,
        suite_id=pipeline.suite_id,
        adapter=adapter_for(pipeline.suite_id),
        classification=pipeline.classification,
        branch_pattern=pipeline.branch_pattern,
        run_mode=pipeline.run_mode,
        enabled=pipeline.enabled,
        is_demo_seed=pipeline.is_demo_seed,
        created_at=pipeline.created_at,
        latest_status=latest.status if latest else None,
        latest_execution_id=latest.id if latest else None,
    )


def _filters(
    project_id: int | None,
    pipeline_id: int | None,
    branch: str | None,
    environment: str | None,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
    include_demo: bool,
) -> dict:
    if status and status not in {"queued", "running", "passed", "failed", "error", "cancelled"}:
        raise HTTPException(status_code=422, detail="Unsupported status")
    return {
        "project_id": project_id,
        "pipeline_id": pipeline_id,
        "branch": branch,
        "environment": environment,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
        "include_demo": include_demo,
    }


@router.get("/suites", response_model=list[SuiteOut])
def get_suites(_role: str = Depends(get_role)) -> list[SuiteOut]:
    return [
        SuiteOut(suite_id=spec.suite_id, adapter=spec.adapter, description=spec.description)
        for spec in CATALOG.values()
    ]


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(session: Session = Depends(get_db), _role: str = Depends(get_role)) -> list[Project]:
    return list(session.scalars(select(Project).options(selectinload(Project.environments)).order_by(Project.name)))


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> Project:
    if session.scalar(select(Project).where(Project.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="Project slug already exists")
    project = Project(**payload.model_dump(), is_demo_seed=False)
    session.add(project)
    session.commit()
    session.refresh(project)
    return _project_or_404(session, project.id)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, session: Session = Depends(get_db), _role: str = Depends(get_role)) -> Project:
    return _project_or_404(session, project_id)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> Project:
    project = _project_or_404(session, project_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    session.commit()
    return _project_or_404(session, project.id)


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> Response:
    project = _project_or_404(session, project_id)
    session.delete(project)
    session.commit()
    return Response(status_code=204)


@router.post("/projects/{project_id}/environments", response_model=EnvironmentOut, status_code=201)
def create_environment(
    project_id: int,
    payload: EnvironmentCreate,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> Environment:
    _project_or_404(session, project_id)
    exists = session.scalar(
        select(Environment).where(Environment.project_id == project_id, Environment.name == payload.name)
    )
    if exists:
        raise HTTPException(status_code=409, detail="Environment already exists")
    environment = Environment(project_id=project_id, is_demo_seed=False, **payload.model_dump())
    session.add(environment)
    session.commit()
    session.refresh(environment)
    return environment


@router.get("/pipelines", response_model=list[PipelineOut])
def list_pipelines(
    project_id: int | None = None,
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> list[PipelineOut]:
    query = select(Pipeline).options(selectinload(Pipeline.project), selectinload(Pipeline.environment))
    if project_id is not None:
        query = query.where(Pipeline.project_id == project_id)
    pipelines = session.scalars(query.order_by(Pipeline.name)).all()
    return [pipeline_out(session, pipeline) for pipeline in pipelines]


@router.post("/pipelines", response_model=PipelineOut, status_code=201)
def create_pipeline(
    payload: PipelineCreate,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> PipelineOut:
    project = _project_or_404(session, payload.project_id)
    if payload.environment_id is not None:
        environment = session.get(Environment, payload.environment_id)
        if environment is None or environment.project_id != project.id:
            raise HTTPException(status_code=422, detail="Environment does not belong to the project")
    pipeline = Pipeline(**payload.model_dump(), is_demo_seed=False)
    session.add(pipeline)
    session.commit()
    session.refresh(pipeline)
    loaded = _pipeline_or_404(session, pipeline.id)
    return pipeline_out(session, loaded)


@router.patch("/pipelines/{pipeline_id}", response_model=PipelineOut)
def update_pipeline(
    pipeline_id: int,
    payload: PipelineUpdate,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> PipelineOut:
    pipeline = _pipeline_or_404(session, pipeline_id)
    data = payload.model_dump(exclude_unset=True)
    if "environment_id" in data and data["environment_id"] is not None:
        environment = session.get(Environment, data["environment_id"])
        if environment is None or environment.project_id != pipeline.project_id:
            raise HTTPException(status_code=422, detail="Environment does not belong to the project")
    for key, value in data.items():
        setattr(pipeline, key, value)
    session.commit()
    return pipeline_out(session, _pipeline_or_404(session, pipeline.id))


@router.get("/executions", response_model=ExecutionPage)
def list_executions(
    project_id: int | None = None,
    pipeline_id: int | None = None,
    branch: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_demo: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> ExecutionPage:
    filters = _filters(project_id, pipeline_id, branch, environment, status, date_from, date_to, include_demo)
    from app.services.analytics import apply_filters

    rows = session.scalars(
        apply_filters(select(Execution), **filters)
        .options(selectinload(Execution.project), selectinload(Execution.pipeline))
        .order_by(Execution.started_at.desc())
    ).all()
    page = rows[offset : offset + limit]
    return ExecutionPage(items=[execution_out(row) for row in page], total=len(rows))


@router.post("/executions", response_model=ExecutionOut, status_code=201)
def create_execution(
    payload: ExecutionCreate,
    actor: str = Query(default="operator", max_length=80),
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> ExecutionOut:
    from app.schemas import ACTOR

    if not ACTOR.fullmatch(actor):
        raise HTTPException(status_code=422, detail="Unsupported actor")
    pipeline = _pipeline_or_404(session, payload.pipeline_id)
    if not pipeline.enabled:
        raise HTTPException(status_code=409, detail="Pipeline is disabled")
    if payload.trigger == "schedule" and pipeline.classification != "scheduled":
        raise HTTPException(status_code=422, detail="Schedule trigger requires a scheduled pipeline")
    branch = payload.branch or pipeline.project.default_branch
    if not branch_matches(pipeline.branch_pattern, branch):
        raise HTTPException(status_code=422, detail="Branch does not match the pipeline pattern")
    environment_name = pipeline.environment.name if pipeline.environment else "dev"
    execution = Execution(
        project_id=pipeline.project_id,
        pipeline_id=pipeline.id,
        environment_name=environment_name,
        status="queued",
        trigger=payload.trigger,
        branch=branch,
        commit_sha=payload.commit_sha,
        pull_request_number=payload.pull_request_number,
        triggered_by=actor,
        is_demo_seed=False,
        started_at=utcnow(),
    )
    session.add(execution)
    session.commit()
    execution_id = execution.id
    schedule_execution(execution_id)
    session.expire_all()
    return execution_out(_execution_or_404(session, execution_id))


@router.get("/executions/{execution_id}", response_model=ExecutionOut)
def get_execution(
    execution_id: int,
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> ExecutionOut:
    return execution_out(_execution_or_404(session, execution_id))


@router.post("/executions/{execution_id}/cancel", response_model=ExecutionOut)
def cancel_execution(
    execution_id: int,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> ExecutionOut:
    _execution_or_404(session, execution_id)
    outcome = request_cancel(execution_id)
    if outcome == "missing":
        raise HTTPException(status_code=404, detail="Execution not found")
    if outcome == "finished":
        raise HTTPException(status_code=409, detail="Execution already finished")
    session.expire_all()
    return execution_out(_execution_or_404(session, execution_id))


@router.get("/executions/{execution_id}/results", response_model=list[TestResultOut])
def list_results(
    execution_id: int,
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> list[TestResult]:
    execution = _execution_or_404(session, execution_id)
    return list(execution.results)


@router.post("/executions/{execution_id}/results", response_model=ExecutionOut)
def ingest_results(
    execution_id: int,
    payload: IngestCreate,
    session: Session = Depends(get_db),
    _role: str = Depends(require_operator),
) -> ExecutionOut:
    execution = _execution_or_404(session, execution_id)
    if execution.pipeline.run_mode != "ingest":
        raise HTTPException(status_code=409, detail="This execution does not accept ingested results")
    if execution.status not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Execution is not awaiting results")
    for result in payload.results:
        session.add(
            TestResult(
                execution_id=execution.id,
                suite_name=result.suite_name,
                name=result.name,
                status=result.status,
                duration_ms=result.duration_ms,
                message=redact(result.message),
                classification=execution.pipeline.classification,
            )
        )
    failed = sum(item.status in {"failed", "error"} for item in payload.results)
    passed = sum(item.status == "passed" for item in payload.results)
    skipped = sum(item.status == "skipped" for item in payload.results)
    execution.total_tests = len(payload.results)
    execution.passed_tests = passed
    execution.failed_tests = failed
    execution.skipped_tests = skipped
    execution.status = "failed" if failed else "passed"
    execution.finished_at = utcnow()
    execution.duration_ms = payload.duration_ms
    if payload.duration_ms is None:
        execution.duration_ms = max(0, int((execution.finished_at - execution.started_at).total_seconds() * 1000))
    session.commit()
    from app.services.notifications import dispatch_notifications

    dispatch_notifications(execution.id)
    session.expire_all()
    return execution_out(_execution_or_404(session, execution_id))


@router.get("/analytics/summary", response_model=SummaryOut)
def analytics_summary(
    project_id: int | None = None,
    pipeline_id: int | None = None,
    branch: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_demo: bool = True,
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> dict:
    filters = _filters(project_id, pipeline_id, branch, environment, status, date_from, date_to, include_demo)
    return summary(session, **filters)


@router.get("/analytics/trends", response_model=list[TrendPoint])
def analytics_trends(
    project_id: int | None = None,
    pipeline_id: int | None = None,
    branch: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_demo: bool = True,
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> list[dict]:
    filters = _filters(project_id, pipeline_id, branch, environment, status, date_from, date_to, include_demo)
    return trends(session, **filters)


@router.get("/analytics/projects", response_model=list[ProjectStat])
def analytics_projects(
    project_id: int | None = None,
    pipeline_id: int | None = None,
    branch: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_demo: bool = True,
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> list[dict]:
    filters = _filters(project_id, pipeline_id, branch, environment, status, date_from, date_to, include_demo)
    return project_stats(session, **filters)


@router.get("/analytics/failures", response_model=list[FailureStat])
def analytics_failures(
    project_id: int | None = None,
    pipeline_id: int | None = None,
    branch: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_demo: bool = True,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> list[dict]:
    filters = _filters(project_id, pipeline_id, branch, environment, status, date_from, date_to, include_demo)
    return failure_stats(session, limit=limit, **filters)


def _render(document: dict, fmt: str, download_name: str) -> Response:
    if fmt == "json":
        from fastapi.responses import JSONResponse

        return JSONResponse(document)
    if fmt == "csv":
        return Response(
            to_csv(document),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{download_name}.csv"'},
        )
    if fmt == "md":
        return Response(
            to_markdown(document),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{download_name}.md"'},
        )
    if fmt == "html":
        return Response(
            to_html(document),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{download_name}.html"'},
        )
    raise HTTPException(status_code=422, detail="Unsupported report format")


@router.get("/reports/executions/{execution_id}")
def execution_report(
    execution_id: int,
    format: str = "json",
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> Response:
    execution = _execution_or_404(session, execution_id)
    document = execution_document(execution, list(execution.results))
    return _render(document, format, f"execution-{execution.id}")


@router.get("/reports/aggregate")
def aggregate_report(
    project_id: int | None = None,
    pipeline_id: int | None = None,
    branch: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    include_demo: bool = True,
    format: str = "json",
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> Response:
    from app.services.analytics import apply_filters

    filters = _filters(project_id, pipeline_id, branch, environment, status, date_from, date_to, include_demo)
    executions = session.scalars(
        apply_filters(select(Execution), **filters)
        .options(selectinload(Execution.project), selectinload(Execution.pipeline))
        .order_by(Execution.started_at.desc())
        .limit(100)
    ).all()
    document = aggregate_document(
        summary(session, **filters),
        project_stats(session, **filters),
        failure_stats(session, **filters),
        list(executions),
    )
    return _render(document, format, "aggregate-report")


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    execution_id: int | None = None,
    session: Session = Depends(get_db),
    _role: str = Depends(get_role),
) -> list[NotificationRecord]:
    query = select(NotificationRecord).order_by(NotificationRecord.id.desc())
    if execution_id is not None:
        query = query.where(NotificationRecord.execution_id == execution_id)
    return list(session.scalars(query.limit(200)))


@router.get("/providers/templates", response_model=list[TemplateOut])
def get_templates(_role: str = Depends(get_role)) -> list[dict]:
    return list_templates()


@router.get("/providers/templates/{provider}/{filename}")
def get_template_content(
    provider: str,
    filename: str,
    _role: str = Depends(get_role),
) -> dict:
    if provider not in {"github", "azure"}:
        raise HTTPException(status_code=404, detail="Unknown provider")
    from app.schemas import TEMPLATE_NAME

    if not TEMPLATE_NAME.fullmatch(filename):
        raise HTTPException(status_code=422, detail="Unsupported template filename")
    try:
        content = read_template(provider, filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Template not found") from exc
    return {"provider": provider, "filename": filename, "content": content}


@router.post("/providers/templates/validate", response_model=TemplateOut)
def validate_template(
    payload: TemplateValidateRequest,
    _role: str = Depends(require_operator),
) -> dict:
    try:
        return validate_submission(payload.provider, payload.filename, payload.content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Template not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/providers/github", response_model=ProviderStatus)
def github_provider(_role: str = Depends(get_role)) -> dict:
    return github_status()


@router.get("/providers/azure", response_model=ProviderStatus)
def azure_provider(_role: str = Depends(get_role)) -> dict:
    return azure_status()
