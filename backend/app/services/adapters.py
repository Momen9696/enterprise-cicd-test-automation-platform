from __future__ import annotations

import sys
from pathlib import Path

from app.catalog import get_suite, marker_for
from app.config import BACKEND_ROOT, get_settings


def pytest_command(suite_dir: Path, junit_path: Path, classification: str) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(suite_dir),
        "-c",
        str(BACKEND_ROOT / "approved_pytest.ini"),
        "--rootdir",
        str(suite_dir),
        "-p",
        "no:cacheprovider",
        "--noconftest",
        "--override-ini",
        "addopts=",
        "-q",
        "--tb=line",
        f"--junitxml={junit_path}",
    ]
    marker = marker_for(classification, "pytest")
    if marker:
        command.extend(["-m", marker])
    return command


def robot_command(suite_dir: Path, junit_path: Path, classification: str) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "robot",
        "--outputdir",
        str(junit_path.parent),
        "--xunit",
        str(junit_path),
        "--log",
        "NONE",
        "--report",
        "NONE",
        "--console",
        "quiet",
    ]
    marker = marker_for(classification, "robot")
    if marker:
        command.extend(["--include", marker])
    command.append(str(suite_dir))
    return command


def playwright_command(suite_dir: Path, junit_path: Path, classification: str) -> list[str]:
    marker = marker_for(classification, "playwright")
    selector = marker or "all"
    return [
        sys.executable,
        "-m",
        "app.services.playwright_suite",
        "--suite",
        str(suite_dir),
        "--junit",
        str(junit_path),
        "--select",
        selector,
    ]


def command_for(suite_id: str, classification: str, junit_path: Path) -> tuple[list[str], Path]:
    settings = get_settings()
    spec = get_suite(suite_id)
    suite_dir = spec.resolve(settings.suite_root)
    if spec.adapter == "pytest":
        return pytest_command(suite_dir, junit_path, classification), suite_dir
    if spec.adapter == "robot":
        return robot_command(suite_dir, junit_path, classification), suite_dir
    if spec.adapter == "playwright":
        return playwright_command(suite_dir, junit_path, classification), suite_dir
    raise ValueError("Adapter is not approved")
