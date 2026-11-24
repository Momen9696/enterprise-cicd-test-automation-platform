from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Environment, Execution, Pipeline, Project, TestResult, utcnow

SUITE_FAILURES = {
    "checkout-pytest": ("test_tax_rounding", "AssertionError: rounded tax did not match"),
    "billing-robot": ("Invoice Total Includes Tax", "Expected 120.0 and calculated 119.99"),
    "portal-playwright": ("Portal heading is visible", "Expected text was not visible: Customer portal"),
}


def seed_if_empty(session: Session) -> bool:
    existing = session.scalar(select(Project.id).limit(1))
    if existing is not None:
        return False
    seed_demo(session)
    return True


def seed_demo(session: Session) -> None:
    projects = [
        Project(
            name="Harbor Checkout",
            slug="harbor-checkout",
            description="Demo seed. Checkout service covered by the approved pytest suite.",
            repository_url="https://github.com/example/harbor-checkout",
            default_branch="main",
            is_demo_seed=True,
        ),
        Project(
            name="Northwind Billing",
            slug="northwind-billing",
            description="Demo seed. Billing checks covered by the approved Robot Framework suite.",
            repository_url="https://github.com/example/northwind-billing",
            default_branch="main",
            is_demo_seed=True,
        ),
        Project(
            name="Lumen Identity Portal",
            slug="lumen-identity",
            description="Demo seed. Portal scenarios covered by the approved Playwright suite.",
            repository_url="https://github.com/example/lumen-identity",
            default_branch="main",
            is_demo_seed=True,
        ),
    ]
    session.add_all(projects)
    session.flush()
    environments: dict[tuple[int, str], Environment] = {}
    for project in projects:
        for name, description in (
            ("dev", "Demo seed. Shared development configuration."),
            ("staging", "Demo seed. Pre-release configuration."),
        ):
            env = Environment(
                project_id=project.id,
                name=name,
                description=description,
                variables={"SERVICE_URL": f"https://{name}.internal.example/{project.slug}"},
                is_demo_seed=True,
            )
            session.add(env)
            environments[(project.id, name)] = env
    session.flush()

    def env_id(project: Project, name: str) -> int:
        return environments[(project.id, name)].id

    harbor, billing, portal = projects
    definitions = [
        (harbor, "Pytest smoke", "local", "smoke", "checkout-pytest", "smoke", "*", "local", "dev"),
        (harbor, "Pytest regression", "local", "regression", "checkout-pytest", "regression", "main", "local", "staging"),
        (harbor, "Checkout pull request", "github_actions", "pull-request-validation", "checkout-pytest", "pr_validation", "*", "ingest", "dev"),
        (billing, "Robot smoke", "local", "smoke", "billing-robot", "smoke", "*", "local", "dev"),
        (billing, "Robot regression", "azure_devops", "regression", "billing-robot", "regression", "main", "local", "staging"),
        (billing, "Weekday billing schedule", "azure_devops", "scheduled", "billing-robot", "scheduled", "main", "ingest", "staging"),
        (portal, "Playwright smoke", "local", "smoke", "portal-playwright", "smoke", "*", "local", "dev"),
        (portal, "Playwright regression", "local", "regression", "portal-playwright", "regression", "main", "local", "staging"),
        (portal, "Portal pull request", "github_actions", "pull-request-validation", "portal-playwright", "pr_validation", "*", "ingest", "dev"),
    ]
    pipelines = []
    for project, name, provider, template_key, suite_id, classification, pattern, run_mode, env_name in definitions:
        pipeline = Pipeline(
            project_id=project.id,
            environment_id=env_id(project, env_name),
            name=name,
            provider=provider,
            template_key=template_key,
            suite_id=suite_id,
            classification=classification,
            branch_pattern=pattern,
            run_mode=run_mode,
            enabled=True,
            is_demo_seed=True,
        )
        session.add(pipeline)
        pipelines.append(pipeline)
    session.flush()

    now = utcnow()
    for index in range(36):
        pipeline = pipelines[index % len(pipelines)]
        project = next(item for item in projects if item.id == pipeline.project_id)
        if index == 0:
            status = "running"
        elif index % 7 == 0:
            status = "failed"
        elif index % 11 == 0:
            status = "error"
        elif index % 17 == 0:
            status = "cancelled"
        else:
            status = "passed"
        started = now - timedelta(days=index % 14, hours=index % 9)
        finished = None if status == "running" else started + timedelta(seconds=20 + (index * 17) % 240)
        duration = None if status == "running" else int((finished - started).total_seconds() * 1000)
        branch = "main" if index % 3 else "feature/tax-rounding"
        environment = "staging" if index % 2 else "dev"
        execution = Execution(
            project_id=project.id,
            pipeline_id=pipeline.id,
            environment_name=environment,
            status=status,
            trigger="schedule" if pipeline.classification == "scheduled" else "manual",
            branch=branch,
            commit_sha=f"{index:040x}",
            started_at=started,
            finished_at=finished,
            duration_ms=duration,
            triggered_by="demo-seed",
            is_demo_seed=True,
        )
        session.add(execution)
        session.flush()
        if status == "running":
            continue
        failure_name, failure_message = SUITE_FAILURES.get(
            pipeline.suite_id, ("test_tax_rounding", "AssertionError: rounded tax did not match")
        )
        cases = [
            ("test_cart_subtotal", "passed", ""),
            ("test_sku_reserved", "passed", ""),
            ("test_discount_code", "passed", ""),
            (failure_name, "failed" if status == "failed" else "passed", failure_message if status == "failed" else ""),
        ]
        if status == "error":
            cases = [("collection", "error", "No tests were collected")]
            execution.error_message = "No tests were collected"
        passed = sum(item[1] == "passed" for item in cases)
        failed = sum(item[1] in {"failed", "error"} for item in cases)
        execution.total_tests = len(cases)
        execution.passed_tests = passed
        execution.failed_tests = failed
        for name, case_status, message in cases:
            session.add(
                TestResult(
                    execution_id=execution.id,
                    suite_name=pipeline.suite_id,
                    name=name,
                    status=case_status,
                    duration_ms=40 + index,
                    message=message,
                    classification=pipeline.classification,
                )
            )
    session.commit()
