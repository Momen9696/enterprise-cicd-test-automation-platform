#!/usr/bin/env python3
"""Check Docker assets. Uses Docker Compose when the CLI is installed."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    backend = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    errors = []
    if "FROM python:3.12-slim" not in backend or "HEALTHCHECK" not in backend or "USER appuser" not in backend:
        errors.append("Backend Dockerfile is missing the expected base image, health check, or user")
    if "FROM node:22-alpine" not in frontend or "nginx" not in frontend or "HEALTHCHECK" not in frontend:
        errors.append("Frontend Dockerfile is missing the expected build or health check")
    services = compose.get("services", {})
    if "backend" not in services or "frontend" not in services:
        errors.append("Compose file needs backend and frontend services")
    if "platform-data" not in compose.get("volumes", {}):
        errors.append("Compose file needs a persistent data volume")
    backend_service = services.get("backend", {})
    if "healthcheck" not in backend_service or "platform-data" not in str(backend_service.get("volumes")):
        errors.append("Backend service needs a health check and the data volume")
    if errors:
        print("\n".join(errors))
        return 1
    docker = shutil.which("docker")
    if docker is None:
        print("Docker CLI is not installed. Compose and Dockerfiles were validated structurally.")
        return 0
    completed = subprocess.run([docker, "compose", "config"], cwd=ROOT, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        print(completed.stderr)
        return completed.returncode
    print("docker compose config succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
