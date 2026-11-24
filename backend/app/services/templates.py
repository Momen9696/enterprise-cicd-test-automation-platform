from __future__ import annotations

from pathlib import Path

import yaml

from app.config import get_settings

GITHUB_FILES = (
    "pytest.yml",
    "robot-framework.yml",
    "playwright.yml",
    "smoke.yml",
    "regression.yml",
    "pull-request-validation.yml",
    "scheduled.yml",
)
AZURE_FILES = GITHUB_FILES

FORBIDDEN = (
    "curl | sh",
    "curl|sh",
    "wget | bash",
    "wget|bash",
    "chmod 777",
    "eval(",
    "powershell -enc",
)


def _forbidden(text: str) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in FORBIDDEN if pattern in lowered]


def _load(text: str) -> dict:
    parsed = yaml.safe_load(text)
    if not isinstance(parsed, dict):
        raise ValueError("Template must be a YAML mapping")
    return parsed


def validate_github(text: str) -> list[str]:
    errors: list[str] = []
    errors.extend(_forbidden(text))
    try:
        document = _load(text)
    except Exception as exc:  # noqa: BLE001
        return [f"YAML parse error: {exc}"]
    trigger = document.get("on", document.get(True))
    if not trigger:
        errors.append("GitHub workflow needs an 'on' trigger")
    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        errors.append("GitHub workflow needs at least one job")
        return errors
    for name, job in jobs.items():
        if not isinstance(job, dict):
            errors.append(f"Job '{name}' is not a mapping")
            continue
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"Job '{name}' needs steps")
            continue
        for step in steps:
            if not isinstance(step, dict):
                errors.append(f"Job '{name}' has a step that is not a mapping")
                continue
            if "run" not in step and "uses" not in step:
                errors.append(f"Job '{name}' has a step without run or uses")
    return errors


def validate_azure(text: str) -> list[str]:
    errors: list[str] = []
    errors.extend(_forbidden(text))
    try:
        document = _load(text)
    except Exception as exc:  # noqa: BLE001
        return [f"YAML parse error: {exc}"]
    has_trigger = any(key in document for key in ("trigger", "pr", "schedules"))
    if not has_trigger:
        errors.append("Azure pipeline needs trigger, pr, or schedules")
    steps = document.get("steps")
    stages = document.get("stages")
    if not steps and not stages:
        errors.append("Azure pipeline needs steps or stages")
    if "pool" not in document and not stages:
        errors.append("Azure pipeline needs a pool")
    return errors


def template_dirs() -> dict[str, Path]:
    root = get_settings().template_root
    return {"github": root / "github", "azure": root / "azure"}


def list_templates() -> list[dict]:
    found = []
    for provider, directory in template_dirs().items():
        expected = GITHUB_FILES if provider == "github" else AZURE_FILES
        for filename in expected:
            path = directory / filename
            if not path.is_file():
                found.append(
                    {
                        "provider": provider,
                        "filename": filename,
                        "template_key": filename.rsplit(".", 1)[0],
                        "valid": False,
                        "errors": ["Template file is missing"],
                    }
                )
                continue
            text = path.read_text(encoding="utf-8")
            errors = validate_github(text) if provider == "github" else validate_azure(text)
            found.append(
                {
                    "provider": provider,
                    "filename": filename,
                    "template_key": filename.rsplit(".", 1)[0],
                    "valid": not errors,
                    "errors": errors,
                }
            )
    return found


def read_template(provider: str, filename: str) -> str:
    directory = template_dirs()[provider]
    path = (directory / filename).resolve()
    if path.parent != directory.resolve() or not path.is_file():
        raise FileNotFoundError(filename)
    text = path.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) > get_settings().max_template_bytes:
        raise ValueError("Template is too large")
    return text


def validate_submission(provider: str, filename: str | None, content: str | None) -> dict:
    if content is None and filename is None:
        raise ValueError("Provide a filename or YAML content")
    if content is not None and len(content.encode("utf-8")) > get_settings().max_template_bytes:
        raise ValueError("Template is too large")
    text = content if content is not None else read_template(provider, filename or "")
    errors = validate_github(text) if provider == "github" else validate_azure(text)
    return {
        "provider": provider,
        "filename": filename or "inline",
        "template_key": (filename or "inline").rsplit(".", 1)[0],
        "valid": not errors,
        "errors": errors,
    }
