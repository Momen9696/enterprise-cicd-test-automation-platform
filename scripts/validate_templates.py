#!/usr/bin/env python3
"""Validate the shipped GitHub Actions and Azure DevOps templates."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.templates import list_templates  # noqa: E402


def main() -> int:
    templates = list_templates()
    failed = [item for item in templates if not item["valid"]]
    print(f"Validated {len(templates)} templates")
    if failed:
        for item in failed:
            print(f"{item['provider']}/{item['filename']}: {item['errors']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
