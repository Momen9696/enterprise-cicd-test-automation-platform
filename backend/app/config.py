from __future__ import annotations

import re
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

_SECRET_KEY = re.compile(r"(SECRET|TOKEN|PASSWORD|PASSWD|PWD|CREDENTIAL|API_KEY|PAT)", re.I)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    platform_api_key: str = "local-operator-key"
    platform_viewer_key: str = "local-viewer-key"
    webhook_secret: str = "local-webhook-secret"
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'platform.db'}"
    suite_root: Path = REPO_ROOT / "sample-suites"
    template_root: Path = REPO_ROOT / "pipelines"
    artifact_root: Path = REPO_ROOT / "data" / "artifacts"
    seed_on_startup: bool = True
    execution_inline: bool = False
    execution_timeout_seconds: int = 120
    github_token: str | None = None
    github_repository: str | None = None
    azure_org: str | None = None
    azure_project: str | None = None
    azure_pat: str | None = None
    notify_webhook_url: str | None = None
    max_webhook_bytes: int = 256_000
    max_template_bytes: int = 64_000

    @field_validator(
        "github_token",
        "github_repository",
        "azure_org",
        "azure_project",
        "azure_pat",
        "notify_webhook_url",
        mode="before",
    )
    @classmethod
    def empty_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("platform_api_key", "platform_viewer_key", "webhook_secret")
    @classmethod
    def long_enough(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Security settings must be at least 8 characters")
        return value

    @field_validator("execution_timeout_seconds")
    @classmethod
    def timeout_bounds(cls, value: int) -> int:
        if not 5 <= value <= 900:
            raise ValueError("Timeout must be between 5 and 900 seconds")
        return value


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None


def sensitive_variable(name: str) -> bool:
    return _SECRET_KEY.search(name) is not None
