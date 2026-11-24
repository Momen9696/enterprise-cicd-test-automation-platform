import hashlib
import hmac
import json

from tests.conftest import OPERATOR, VIEWER


def sign(body: bytes, secret: str = "test-webhook-secret") -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def create_project(client, slug="harbor-checkout", repo="https://github.com/example/harbor-checkout"):
    response = client.post(
        "/api/projects",
        headers=OPERATOR,
        json={
            "name": "Harbor Checkout",
            "slug": slug,
            "description": "Service under test",
            "repository_url": repo,
            "default_branch": "main",
        },
    )
    assert response.status_code == 201, response.text
    project = response.json()
    environment = client.post(
        f"/api/projects/{project['id']}/environments",
        headers=OPERATOR,
        json={"name": "dev", "description": "Dev", "variables": {"SERVICE_URL": "https://dev.example"}},
    )
    assert environment.status_code == 201, environment.text
    return project, environment.json()


def create_pipeline(client, project, environment, **overrides):
    payload = {
        "project_id": project["id"],
        "environment_id": environment["id"],
        "name": "Checkout smoke",
        "provider": "local",
        "template_key": "smoke",
        "suite_id": "checkout-pytest",
        "classification": "smoke",
        "branch_pattern": "*",
        "run_mode": "local",
        "enabled": True,
    }
    payload.update(overrides)
    response = client.post("/api/pipelines", headers=OPERATOR, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_and_viewer_authorization(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects", headers=VIEWER).status_code == 200
    denied = client.post(
        "/api/projects",
        headers=VIEWER,
        json={"name": "Nope", "slug": "nope", "default_branch": "main"},
    )
    assert denied.status_code == 403


def test_project_environment_and_pipeline_crud(client):
    project, environment = create_project(client)
    listed = client.get("/api/projects", headers=OPERATOR).json()
    assert listed[0]["slug"] == "harbor-checkout"
    assert listed[0]["is_demo_seed"] is False
    updated = client.patch(
        f"/api/projects/{project['id']}",
        headers=OPERATOR,
        json={"description": "Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated"
    pipeline = create_pipeline(client, project, environment)
    assert pipeline["adapter"] == "pytest"
    toggled = client.patch(
        f"/api/pipelines/{pipeline['id']}",
        headers=OPERATOR,
        json={"enabled": False},
    )
    assert toggled.json()["enabled"] is False
    blocked = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": pipeline["id"], "trigger": "manual"},
    )
    assert blocked.status_code == 409


def test_invalid_configuration_is_rejected(client):
    project, environment = create_project(client)
    traversal = client.post(
        "/api/pipelines",
        headers=OPERATOR,
        json={
            "project_id": project["id"],
            "environment_id": environment["id"],
            "name": "Bad suite",
            "provider": "local",
            "template_key": "smoke",
            "suite_id": "../checkout-pytest",
            "classification": "smoke",
            "run_mode": "local",
        },
    )
    assert traversal.status_code == 422
    secret_env = client.post(
        f"/api/projects/{project['id']}/environments",
        headers=OPERATOR,
        json={"name": "qa", "variables": {"API_TOKEN": "should-not-store"}},
    )
    assert secret_env.status_code == 422
    command = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": 1, "trigger": "manual", "command": "rm -rf /"},
    )
    assert command.status_code == 422
    branch = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": 1, "branch": "main;touch /tmp/pwned", "trigger": "manual"},
    )
    assert branch.status_code == 422


def test_pytest_smoke_lifecycle_and_notifications(client):
    project, environment = create_project(client)
    pipeline = create_pipeline(client, project, environment)
    response = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": pipeline["id"], "branch": "main", "commit_sha": "abc1234", "trigger": "manual"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "passed"
    assert body["passed_tests"] == 2
    assert body["failed_tests"] == 0
    assert body["duration_ms"] is not None
    assert body["is_demo_seed"] is False
    results = client.get(f"/api/executions/{body['id']}/results", headers=OPERATOR).json()
    assert {item["name"] for item in results} == {"test_cart_subtotal", "test_sku_reserved"}
    notes = client.get(f"/api/notifications?execution_id={body['id']}", headers=VIEWER).json()
    assert {item["channel"] for item in notes} == {"log", "webhook"}
    assert any(item["status"] == "skipped" for item in notes)


def test_failure_handling_and_robot_success(client):
    project, environment = create_project(client, slug="billing-api")
    failing = create_pipeline(
        client,
        project,
        environment,
        name="Known failure",
        suite_id="checkout-failures",
        classification="regression",
        template_key="regression",
    )
    failed = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": failing["id"], "trigger": "manual"},
    ).json()
    assert failed["status"] == "failed"
    assert failed["failed_tests"] == 1
    analysis = client.get("/api/analytics/failures?include_demo=false", headers=OPERATOR).json()
    assert analysis[0]["name"] == "test_tax_rounding_legacy"
    robot = create_pipeline(
        client,
        project,
        environment,
        name="Billing smoke",
        suite_id="billing-robot",
        classification="smoke",
        template_key="smoke",
    )
    passed = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": robot["id"], "trigger": "manual"},
    )
    assert passed.status_code == 201, passed.text
    assert passed.json()["status"] == "passed"
    assert passed.json()["passed_tests"] == 1


def test_playwright_adapter_records_catalog_scenarios(client):
    project, environment = create_project(client, slug="lumen-portal")
    pipeline = create_pipeline(
        client,
        project,
        environment,
        name="Portal smoke",
        suite_id="portal-playwright",
        classification="smoke",
        template_key="smoke",
    )
    response = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": pipeline["id"], "trigger": "manual"},
    )
    body = response.json()
    assert body["status"] in {"passed", "failed"}
    assert body["total_tests"] == 1
    results = client.get(f"/api/executions/{body['id']}/results", headers=OPERATOR).json()
    assert results[0]["name"] == "Portal heading is visible"
    assert "test-operator" not in json.dumps(results)


def test_ingest_cancel_and_schedule_rules(client):
    project, environment = create_project(client, slug="scheduled-billing")
    pipeline = create_pipeline(
        client,
        project,
        environment,
        name="Weekday",
        provider="azure_devops",
        template_key="scheduled",
        classification="scheduled",
        run_mode="ingest",
        branch_pattern="main",
    )
    created = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": pipeline["id"], "trigger": "schedule", "branch": "main"},
    )
    assert created.status_code == 201, created.text
    execution_id = created.json()["id"]
    assert created.json()["status"] == "running"
    rejected = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": pipeline["id"], "trigger": "schedule", "branch": "feature/other"},
    )
    assert rejected.status_code == 422
    smoke = create_pipeline(client, project, environment, name="Not scheduled")
    wrong_trigger = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": smoke["id"], "trigger": "schedule"},
    )
    assert wrong_trigger.status_code == 422
    ingested = client.post(
        f"/api/executions/{execution_id}/results",
        headers=OPERATOR,
        json={
            "results": [
                {"name": "test_cart_subtotal", "status": "passed", "duration_ms": 12, "message": ""},
                {
                    "name": "test_tax_rounding",
                    "status": "failed",
                    "duration_ms": 20,
                    "message": "token=supersecretvalue <script>alert(1)</script>",
                },
            ]
        },
    )
    assert ingested.status_code == 200, ingested.text
    assert ingested.json()["status"] == "failed"
    stored = client.get(f"/api/executions/{execution_id}/results", headers=OPERATOR).json()
    assert "supersecretvalue" not in json.dumps(stored)
    assert "[redacted]" in json.dumps(stored)
    again = client.post(
        f"/api/executions/{execution_id}/results",
        headers=OPERATOR,
        json={"results": [{"name": "test_cart_subtotal", "status": "passed"}]},
    )
    assert again.status_code == 409
    waiting = client.post(
        "/api/executions",
        headers=OPERATOR,
        json={"pipeline_id": pipeline["id"], "trigger": "schedule"},
    ).json()
    cancelled = client.post(f"/api/executions/{waiting['id']}/cancel", headers=OPERATOR)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    late = client.post(
        f"/api/executions/{waiting['id']}/results",
        headers=OPERATOR,
        json={"results": [{"name": "test_cart_subtotal", "status": "passed"}]},
    )
    assert late.status_code == 409


def test_webhooks_require_signatures_and_are_idempotent(client):
    project, environment = create_project(client)
    create_pipeline(
        client,
        project,
        environment,
        name="PR gate",
        provider="github_actions",
        template_key="pull-request-validation",
        classification="pr_validation",
        run_mode="ingest",
    )
    payload = {
        "action": "opened",
        "repository": {"full_name": "example/harbor-checkout"},
        "pull_request": {"number": 18, "head": {"ref": "feature/tax-rounding", "sha": "abc1234def"}},
    }
    raw = json.dumps(payload).encode()
    rejected = client.post("/api/webhooks/github", content=raw, headers={"Content-Type": "application/json"})
    assert rejected.status_code == 401
    forged = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert forged.status_code == 401
    accepted = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sign(raw),
            "X-GitHub-Delivery": "delivery-1",
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["executions"]
    duplicate = client.post(
        "/api/webhooks/github",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sign(raw),
            "X-GitHub-Delivery": "delivery-1",
        },
    )
    assert duplicate.json()["duplicate"] is True
    azure_payload = json.dumps(
        {
            "repository": {"full_name": "example/harbor-checkout"},
            "pullRequest": {"pullRequestId": 4, "head": {"name": "feature/tax-rounding", "sha": "abc1234"}},
        }
    ).encode()
    azure = client.post(
        "/api/webhooks/azure",
        content=azure_payload,
        headers={
            "Content-Type": "application/json",
            "X-Platform-Signature": sign(azure_payload),
            "X-Azure-Delivery": "az-1",
        },
    )
    assert azure.status_code == 200
    assert azure.json()["executions"] == []


def test_seed_analytics_reports_and_filters(client, session):
    from app.seed import seed_demo

    seed_demo(session)
    summary = client.get("/api/analytics/summary", headers=OPERATOR).json()
    assert summary["source"] == "database"
    assert summary["total_runs"] == 36
    assert summary["passed_runs"] == 25
    assert summary["failed_runs"] == 5
    assert summary["error_runs"] == 3
    assert summary["running_runs"] == 1
    assert summary["cancelled_runs"] == 2
    assert summary["demo_seed_runs"] == 36
    assert summary["success_rate"] == 75.8
    assert summary["average_duration_ms"] > 0
    hidden = client.get("/api/analytics/summary?include_demo=false", headers=OPERATOR).json()
    assert hidden["total_runs"] == 0
    branch = client.get("/api/analytics/summary?branch=feature/tax-rounding", headers=OPERATOR).json()
    assert branch["total_runs"] == 12
    staging = client.get("/api/analytics/summary?environment=staging", headers=OPERATOR).json()
    assert staging["total_runs"] == 18
    empty = client.get("/api/analytics/summary?date_from=2099-01-01", headers=OPERATOR).json()
    assert empty["total_runs"] == 0
    projects = client.get("/api/analytics/projects", headers=OPERATOR).json()
    assert {item["project_name"] for item in projects} == {
        "Harbor Checkout",
        "Northwind Billing",
        "Lumen Identity Portal",
    }
    trends = client.get("/api/analytics/trends", headers=OPERATOR).json()
    assert trends
    failures = client.get("/api/analytics/failures", headers=OPERATOR).json()
    assert any(item["name"] == "test_tax_rounding" for item in failures)
    report = client.get("/api/reports/aggregate?format=html", headers=OPERATOR)
    assert report.status_code == 200
    assert "Aggregate execution report" in report.text
    assert "<script>" not in report.text
    executions = client.get("/api/executions?status=failed&limit=5", headers=OPERATOR).json()
    assert executions["total"] == 5
    assert len(executions["items"]) == 5
    execution_id = executions["items"][0]["id"]
    markdown = client.get(f"/api/reports/executions/{execution_id}?format=md", headers=VIEWER)
    assert "Demo seed: True" in markdown.text or "demo" in markdown.text.lower()
    csv_report = client.get("/api/reports/aggregate?format=csv", headers=OPERATOR)
    assert "project" in csv_report.text.splitlines()[0]


def test_templates_providers_and_contract(client):
    templates = client.get("/api/providers/templates", headers=VIEWER)
    assert templates.status_code == 200
    body = templates.json()
    assert len(body) == 14
    assert all(item["valid"] for item in body)
    bad = client.post(
        "/api/providers/templates/validate",
        headers=OPERATOR,
        json={"provider": "github", "content": "name: bad\njobs:\n  one:\n    steps:\n      - run: curl | sh\n"},
    )
    assert bad.status_code == 200
    assert bad.json()["valid"] is False
    missing = client.get("/api/providers/templates/github/not-real.yml", headers=OPERATOR)
    assert missing.status_code == 404
    content = client.get("/api/providers/templates/azure/pytest.yml", headers=VIEWER)
    assert "pytest" in content.json()["content"]
    github = client.get("/api/providers/github", headers=VIEWER).json()
    azure = client.get("/api/providers/azure", headers=VIEWER).json()
    assert github["configured"] is False
    assert azure["configured"] is False
    assert "token" not in github["detail"].lower() or "not configured" in github["detail"].lower()
    spec = client.get("/openapi.json").json()
    for path in (
        "/health",
        "/api/projects",
        "/api/pipelines",
        "/api/executions",
        "/api/analytics/summary",
        "/api/analytics/trends",
        "/api/analytics/projects",
        "/api/analytics/failures",
        "/api/reports/aggregate",
        "/api/providers/templates",
        "/api/webhooks/github",
        "/api/webhooks/azure",
    ):
        assert path in spec["paths"]
    suites = client.get("/api/suites", headers=VIEWER).json()
    assert {item["suite_id"] for item in suites} == {
        "checkout-pytest",
        "checkout-failures",
        "billing-robot",
        "portal-playwright",
    }


def test_subprocess_environment_strips_secrets(monkeypatch):
    monkeypatch.setenv("PLATFORM_API_KEY", "test-operator")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_shouldnotpass")
    from app.services.process import build_subprocess_env

    env = build_subprocess_env()
    assert "PLATFORM_API_KEY" not in env
    assert "WEBHOOK_SECRET" not in env
    assert "GITHUB_TOKEN" not in env
    assert "ghp_shouldnotpass" not in " ".join(env.values())


def test_playwright_module_rejects_unapproved_directories(tmp_path):
    from app.services.playwright_suite import main

    code = main(["--suite", str(tmp_path), "--junit", str(tmp_path / "junit.xml"), "--select", "smoke"])
    assert code == 2


def test_publish_script_parses_junit(tmp_path):
    import importlib.util

    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0"?>
        <testsuite name="checkout">
          <testcase classname="checkout" name="test_cart_subtotal" time="0.01"/>
          <testcase classname="checkout" name="test_tax_rounding" time="0.02">
            <failure message="rounded tax did not match"/>
          </testcase>
        </testsuite>
        """,
        encoding="utf-8",
    )
    path = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "pipelines"
        / "scripts"
        / "publish_results.py"
    )
    spec = importlib.util.spec_from_file_location("publish_results", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    results = module.parse_junit(junit)
    assert results[1]["status"] == "failed"
    assert results[0]["name"] == "test_cart_subtotal"


def test_redacting_formatter_hides_assignments():
    import logging

    from app.security import RedactFormatter

    record = logging.LogRecord("platform", logging.INFO, __file__, 1, "token=supersecretvalue", None, None)
    rendered = RedactFormatter("%(message)s").format(record)
    assert "supersecretvalue" not in rendered
    assert "[redacted]" in rendered


def test_github_provider_does_not_echo_token(client, monkeypatch):
    from app.config import reset_settings

    monkeypatch.setenv("GITHUB_TOKEN", "ghp_exampletokenvalue")
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/harbor-checkout")
    reset_settings()

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"workflows": [{"name": "CI", "path": ".github/workflows/ci.yml", "state": "active"}]}

    monkeypatch.setattr("app.services.providers.httpx.get", lambda *args, **kwargs: FakeResponse())
    payload = client.get("/api/providers/github", headers=OPERATOR).json()
    assert payload["configured"] is True
    assert payload["remote_count"] == 1
    assert "ghp_" not in json.dumps(payload)
    reset_settings()
