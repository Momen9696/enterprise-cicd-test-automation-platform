from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.catalog import ADAPTERS, CATALOG, CLASSIFICATIONS, PROVIDERS, RUN_MODES, STATUSES, TRIGGERS
from app.config import sensitive_variable

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BRANCH = re.compile(r"^[A-Za-z0-9._/*-]{1,200}$")
SHA = re.compile(r"^[a-fA-F0-9]{7,40}$")
ENV_NAME = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
VAR_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,40}$")
ACTOR = re.compile(r"^[A-Za-z0-9_.@-]{1,80}$")
TEST_NAME = re.compile(r"^[A-Za-z0-9_.:/ ()-]{1,200}$")
TEMPLATE_NAME = re.compile(r"^[a-z0-9-]+\.ya?ml$")


def _branch(value: str) -> str:
    if not BRANCH.fullmatch(value) or ".." in value:
        raise ValueError("Branch contains unsupported characters")
    return value


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=500)
    repository_url: str | None = Field(default=None, max_length=300)
    default_branch: str = "main"

    @field_validator("slug")
    @classmethod
    def slug_ok(cls, value: str) -> str:
        if not SLUG.fullmatch(value):
            raise ValueError("Slug must be lowercase words separated by hyphens")
        return value

    @field_validator("default_branch")
    @classmethod
    def branch_ok(cls, value: str) -> str:
        return _branch(value)

    @field_validator("repository_url")
    @classmethod
    def repo_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith(("https://", "http://")):
            raise ValueError("Repository URL must start with http:// or https://")
        return value


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    repository_url: str | None = None
    default_branch: str | None = None

    @field_validator("default_branch")
    @classmethod
    def branch_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _branch(value)


class EnvironmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = Field(default="", max_length=300)
    variables: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_ok(cls, value: str) -> str:
        if not ENV_NAME.fullmatch(value):
            raise ValueError("Environment name must be lowercase")
        return value

    @field_validator("variables")
    @classmethod
    def vars_ok(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 30:
            raise ValueError("Too many variables")
        cleaned: dict[str, str] = {}
        for key, raw in value.items():
            if not VAR_NAME.fullmatch(key):
                raise ValueError(f"Unsupported variable name '{key}'")
            if sensitive_variable(key):
                raise ValueError(f"Refusing to store sensitive variable '{key}'")
            if not isinstance(raw, str) or len(raw) > 200:
                raise ValueError(f"Variable '{key}' must be a short string")
            cleaned[key] = raw
        return cleaned


class EnvironmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: str
    variables: dict
    is_demo_seed: bool
    created_at: datetime


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    repository_url: str | None
    default_branch: str
    is_demo_seed: bool
    created_at: datetime
    environments: list[EnvironmentOut] = Field(default_factory=list)


class PipelineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: int
    environment_id: int | None = None
    name: str = Field(min_length=3, max_length=140)
    provider: str
    template_key: str = Field(min_length=3, max_length=80)
    suite_id: str
    classification: str
    branch_pattern: str = "*"
    run_mode: str = "local"
    enabled: bool = True

    @field_validator("provider")
    @classmethod
    def provider_ok(cls, value: str) -> str:
        if value not in PROVIDERS:
            raise ValueError("Unsupported provider")
        return value

    @field_validator("suite_id")
    @classmethod
    def suite_ok(cls, value: str) -> str:
        if value not in CATALOG:
            raise ValueError("Suite is not in the approved catalog")
        return value

    @field_validator("classification")
    @classmethod
    def class_ok(cls, value: str) -> str:
        if value not in CLASSIFICATIONS:
            raise ValueError("Unsupported classification")
        return value

    @field_validator("run_mode")
    @classmethod
    def mode_ok(cls, value: str) -> str:
        if value not in RUN_MODES:
            raise ValueError("Unsupported run mode")
        return value

    @field_validator("branch_pattern")
    @classmethod
    def pattern_ok(cls, value: str) -> str:
        return _branch(value)

    @field_validator("template_key")
    @classmethod
    def template_ok(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9-]{3,80}", value):
            raise ValueError("Unsupported template key")
        return value


class PipelineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=3, max_length=140)
    enabled: bool | None = None
    branch_pattern: str | None = None
    environment_id: int | None = None

    @field_validator("branch_pattern")
    @classmethod
    def pattern_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _branch(value)


class PipelineOut(BaseModel):
    id: int
    project_id: int
    project_name: str
    environment_id: int | None
    environment_name: str | None
    name: str
    provider: str
    template_key: str
    suite_id: str
    adapter: str
    classification: str
    branch_pattern: str
    run_mode: str
    enabled: bool
    is_demo_seed: bool
    created_at: datetime
    latest_status: str | None = None
    latest_execution_id: int | None = None


class ExecutionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_id: int
    branch: str | None = None
    commit_sha: str | None = None
    pull_request_number: int | None = Field(default=None, ge=1, le=1_000_000)
    trigger: str = "manual"

    @field_validator("branch")
    @classmethod
    def branch_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _branch(value)

    @field_validator("commit_sha")
    @classmethod
    def sha_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not SHA.fullmatch(value):
            raise ValueError("Commit SHA must be 7 to 40 hex characters")
        return value

    @field_validator("trigger")
    @classmethod
    def trigger_ok(cls, value: str) -> str:
        if value not in {"manual", "schedule"}:
            raise ValueError("This endpoint accepts manual or schedule triggers")
        return value


class ResultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    suite_name: str = Field(default="", max_length=200)
    status: str
    duration_ms: int = Field(default=0, ge=0, le=3_600_000)
    message: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def name_ok(cls, value: str) -> str:
        if not TEST_NAME.fullmatch(value):
            raise ValueError("Unsupported test name")
        return value

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str) -> str:
        if value not in {"passed", "failed", "skipped", "error"}:
            raise ValueError("Unsupported result status")
        return value


class IngestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[ResultIn] = Field(min_length=1, max_length=500)
    duration_ms: int | None = Field(default=None, ge=0, le=3_600_000)


class TestResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    suite_name: str
    name: str
    status: str
    duration_ms: int
    message: str
    classification: str


class ExecutionOut(BaseModel):
    id: int
    project_id: int
    project_name: str
    pipeline_id: int
    pipeline_name: str
    environment_name: str
    status: str
    trigger: str
    branch: str
    commit_sha: str | None
    pull_request_number: int | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_message: str | None
    triggered_by: str
    is_demo_seed: bool
    provider: str
    classification: str


class ExecutionPage(BaseModel):
    items: list[ExecutionOut]
    total: int


class SummaryOut(BaseModel):
    total_runs: int
    passed_runs: int
    failed_runs: int
    error_runs: int
    running_runs: int
    cancelled_runs: int
    average_duration_ms: int
    success_rate: float
    test_pass_rate: float
    demo_seed_runs: int
    source: str = "database"


class TrendPoint(BaseModel):
    date: str
    passed: int
    failed: int
    error: int


class ProjectStat(BaseModel):
    project_id: int
    project_name: str
    runs: int
    passed: int
    failed: int
    average_duration_ms: int
    success_rate: float


class FailureStat(BaseModel):
    name: str
    suite_name: str
    failures: int
    last_message: str
    last_seen: datetime
    project_name: str


class SuiteOut(BaseModel):
    suite_id: str
    adapter: str
    description: str


class TemplateOut(BaseModel):
    provider: str
    filename: str
    template_key: str
    valid: bool
    errors: list[str]


class ProviderStatus(BaseModel):
    provider: str
    configured: bool
    reachable: bool | None = None
    detail: str
    remote_count: int = 0


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: int
    channel: str
    status: str
    summary: str
    created_at: datetime


class ActorQuery(BaseModel):
    actor: str = "operator"

    @field_validator("actor")
    @classmethod
    def actor_ok(cls, value: str) -> str:
        if not ACTOR.fullmatch(value):
            raise ValueError("Unsupported actor")
        return value


class TemplateValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    filename: str | None = None
    content: str | None = None

    @field_validator("provider")
    @classmethod
    def provider_ok(cls, value: str) -> str:
        if value not in {"github", "azure"}:
            raise ValueError("Provider must be github or azure")
        return value

    @field_validator("filename")
    @classmethod
    def file_ok(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not TEMPLATE_NAME.fullmatch(value):
            raise ValueError("Unsupported template filename")
        return value


def adapter_for(suite_id: str) -> str:
    adapter = CATALOG[suite_id].adapter
    if adapter not in ADAPTERS:
        raise ValueError("Adapter is not approved")
    return adapter


def ensure_status(value: str) -> str:
    if value not in STATUSES:
        raise ValueError("Unsupported status")
    return value


def ensure_trigger(value: str) -> str:
    if value not in TRIGGERS:
        raise ValueError("Unsupported trigger")
    return value
