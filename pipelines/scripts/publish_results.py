#!/usr/bin/env python3
"""Publish a JUnit file to an ingest-mode execution.

Copy this script into a project that already created an execution and stored
its id. The API key is read from the environment and is never printed.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_junit(path: Path) -> list[dict]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    results = []
    for suite in suites:
        for node in suite.findall("testcase"):
            status = "passed"
            message = ""
            if node.find("failure") is not None:
                status = "failed"
                message = node.find("failure").attrib.get("message", "")
            elif node.find("error") is not None:
                status = "error"
                message = node.find("error").attrib.get("message", "")
            elif node.find("skipped") is not None:
                status = "skipped"
            seconds = float(node.attrib.get("time", "0") or 0)
            results.append(
                {
                    "name": node.attrib.get("name", "unnamed")[:200],
                    "suite_name": node.attrib.get("classname", suite.attrib.get("name", ""))[:200],
                    "status": status,
                    "duration_ms": max(0, int(seconds * 1000)),
                    "message": message[:2000],
                }
            )
    return results


def main() -> int:
    base = os.environ.get("PLATFORM_URL", "").rstrip("/")
    execution_id = os.environ.get("EXECUTION_ID", "")
    api_key = os.environ.get("PLATFORM_API_KEY", "")
    junit_path = Path(os.environ.get("JUNIT_PATH", "results/junit.xml"))
    if not base or not execution_id or not api_key:
        print("PLATFORM_URL, EXECUTION_ID, and PLATFORM_API_KEY are required", file=sys.stderr)
        return 2
    if not execution_id.isdigit():
        print("EXECUTION_ID must be a number", file=sys.stderr)
        return 2
    if not junit_path.is_file():
        print("JUnit file was not found", file=sys.stderr)
        return 2
    payload = json.dumps({"results": parse_junit(junit_path)}).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/api/executions/{execution_id}/results",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"Published results with status {response.status}")
    except urllib.error.HTTPError as exc:
        print(f"Publish failed with status {exc.code}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
