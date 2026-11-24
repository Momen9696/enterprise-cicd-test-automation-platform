#!/usr/bin/env python3
"""Confirm the documentation set is present and not a stub."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "docs/architecture.md",
    "docs/setup.md",
    "docs/pipeline-integration.md",
    "docs/security.md",
    "docs/api.md",
    "docs/portfolio/upwork-case-study.md",
    "docs/portfolio/upwork-description.md",
    "docs/execution-evidence.md",
)


def main() -> int:
    missing = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or len(path.read_text(encoding="utf-8").strip()) < 200:
            missing.append(relative)
    if missing:
        print("Documentation is missing or too short:")
        print("\n".join(missing))
        return 1
    print(f"Documentation validation passed ({len(REQUIRED)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
