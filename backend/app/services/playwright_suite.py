from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from app.catalog import get_suite
from app.config import get_settings
from app.security import redact
from app.services.junit import ParsedCase, write_junit

SELECTORS = {"smoke": "smoke", "regression": "regression", "all": None}


def _load_scenarios(suite_dir: Path, selector: str) -> list[dict]:
    document = json.loads((suite_dir / "scenarios.json").read_text(encoding="utf-8"))
    scenarios = document.get("scenarios", [])
    if not isinstance(scenarios, list):
        raise ValueError("scenarios.json is invalid")
    wanted = SELECTORS[selector]
    chosen = []
    for item in scenarios:
        if not isinstance(item, dict):
            continue
        classification = str(item.get("classification", ""))
        if wanted is not None and classification != wanted:
            continue
        name = str(item.get("name", ""))
        fixture = str(item.get("fixture", ""))
        expect = str(item.get("expect_text", ""))
        if not name or not fixture or not expect or ".." in fixture:
            raise ValueError("Scenario is incomplete")
        chosen.append(
            {"name": name, "fixture": fixture, "expect_text": expect, "classification": classification}
        )
    return chosen


def _assert_local_file(suite_dir: Path, fixture: str) -> Path:
    path = (suite_dir / fixture).resolve()
    root = suite_dir.resolve()
    if path != root and root not in path.parents:
        raise ValueError("Fixture escapes the suite")
    if path.suffix.lower() not in {".html", ".htm"} or not path.is_file():
        raise ValueError("Fixture must be an HTML file inside the suite")
    return path


def run(suite_dir: Path, junit_path: Path, selector: str) -> int:
    scenarios = _load_scenarios(suite_dir, selector)
    cases: list[ParsedCase] = []
    browser_error = ""
    playwright = None
    try:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright
    except Exception as exc:  # noqa: BLE001
        browser_error = redact(str(exc))
    if playwright is None:
        for scenario in scenarios:
            cases.append(
                ParsedCase(
                    scenario["name"],
                    "portal-playwright",
                    "error",
                    0,
                    browser_error or "Playwright is not installed",
                )
            )
        write_junit(junit_path, cases)
        return 1
    with playwright() as manager:
        try:
            browser = manager.chromium.launch(headless=True)
        except Exception as exc:  # noqa: BLE001
            message = redact(str(exc))[:500]
            for scenario in scenarios:
                cases.append(ParsedCase(scenario["name"], "portal-playwright", "error", 0, message))
            write_junit(junit_path, cases)
            return 1
        try:
            page = browser.new_page()
            for scenario in scenarios:
                started = time.perf_counter()
                try:
                    fixture = _assert_local_file(suite_dir, scenario["fixture"])
                    page.goto(fixture.as_uri(), timeout=15_000)
                    body = page.inner_text("body")
                    ok = scenario["expect_text"] in body
                    cases.append(
                        ParsedCase(
                            scenario["name"],
                            "portal-playwright",
                            "passed" if ok else "failed",
                            int((time.perf_counter() - started) * 1000),
                            "" if ok else f"Expected text was not visible: {scenario['expect_text']}",
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    cases.append(
                        ParsedCase(
                            scenario["name"],
                            "portal-playwright",
                            "error",
                            int((time.perf_counter() - started) * 1000),
                            redact(str(exc))[:500],
                        )
                    )
        finally:
            browser.close()
    write_junit(junit_path, cases)
    return 0 if cases and all(case.status == "passed" for case in cases) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="playwright-suite")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--junit", required=True)
    parser.add_argument("--select", required=True, choices=sorted(SELECTORS))
    args = parser.parse_args(argv)
    settings = get_settings()
    suite_dir = Path(args.suite).resolve()
    approved = False
    for spec in (get_suite("portal-playwright"),):
        if suite_dir == spec.resolve(settings.suite_root):
            approved = True
    if not approved:
        print("Suite is not an approved Playwright catalog entry", file=sys.stderr)
        return 2
    junit = Path(args.junit).resolve()
    artifact_root = settings.artifact_root.resolve()
    if artifact_root not in junit.parents and junit.parent != artifact_root:
        print("JUnit path is outside the artifact root", file=sys.stderr)
        return 2
    return run(suite_dir, junit, args.select)


if __name__ == "__main__":
    raise SystemExit(main())
