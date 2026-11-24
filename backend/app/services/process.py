from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
import threading
from pathlib import Path

from app.config import BACKEND_ROOT, get_settings

_LOCK = threading.Lock()
_PROCS: dict[int, subprocess.Popen[bytes]] = {}

_ENV_ALLOW = {
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SYSTEMROOT",
    "WINDIR",
    "PLAYWRIGHT_BROWSERS_PATH",
    "ARTIFACT_ROOT",
    "SUITE_ROOT",
    "TEMPLATE_ROOT",
}
_APPROVED_MODULES = {"pytest", "robot", "app.services.playwright_suite"}


def build_subprocess_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in _ENV_ALLOW if key in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(BACKEND_ROOT)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def register_process(execution_id: int, process: subprocess.Popen[bytes]) -> None:
    with _LOCK:
        _PROCS[execution_id] = process


def unregister_process(execution_id: int) -> None:
    with _LOCK:
        _PROCS.pop(execution_id, None)


def terminate_process(execution_id: int) -> bool:
    with _LOCK:
        process = _PROCS.get(execution_id)
    if process is None or process.poll() is not None:
        return False
    process.terminate()
    return True


def run_command(
    execution_id: int,
    command: list[str],
    cwd: Path,
    timeout: int | None = None,
) -> tuple[int, bool, str]:
    if not command or command[0] != sys.executable or "-m" not in command:
        raise RuntimeError("Refusing a command that is not an approved module")
    module = command[command.index("-m") + 1]
    if module not in _APPROVED_MODULES:
        raise RuntimeError("Refusing a command that is not an approved module")
    settings = get_settings()
    process = subprocess.Popen(  # nosec B603
        command,
        cwd=str(cwd),
        env=build_subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    register_process(execution_id, process)
    timed_out = False
    try:
        _stdout, stderr = process.communicate(timeout=timeout or settings.execution_timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        _stdout, stderr = process.communicate()
        timed_out = True
    finally:
        unregister_process(execution_id)
    code = process.returncode if process.returncode is not None else 1
    tail = stderr.decode("utf-8", errors="replace")[-500:]
    return code, timed_out, tail
