from __future__ import annotations

import hmac
import logging
import re
from typing import Literal

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

from app.config import get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
Role = Literal["operator", "viewer"]

_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|token|password|passwd|secret|pat|authorization)\b\s*[:=]\s*\S+"
)


def redact(text: str) -> str:
    return _ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[redacted]", text)


class RedactFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def install_redacting_logs() -> None:
    formatter = RedactFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(formatter)
    root.setLevel(logging.INFO)


def verify_signature(body: bytes, header: str | None, secret: str) -> bool:
    if not header or not secret:
        return False
    provided = header.strip()
    if provided.lower().startswith("sha256="):
        provided = provided.split("=", 1)[1].strip()
    expected = hmac.new(secret.encode("utf-8"), body, "sha256").hexdigest()
    return hmac.compare_digest(expected, provided)


def role_for_key(key: str | None) -> Role | None:
    settings = get_settings()
    if key is None:
        return None
    if hmac.compare_digest(key, settings.platform_api_key):
        return "operator"
    if hmac.compare_digest(key, settings.platform_viewer_key):
        return "viewer"
    return None


async def get_role(key: str | None = Depends(api_key_header)) -> Role:
    role = role_for_key(key)
    if role is None:
        raise HTTPException(status_code=401, detail="Valid API key required")
    return role


async def require_operator(role: Role = Depends(get_role)) -> Role:
    if role != "operator":
        raise HTTPException(status_code=403, detail="Operator API key required")
    return role


def client_host(request: Request) -> str:
    if request.client is None:
        return "unknown"
    return request.client.host
