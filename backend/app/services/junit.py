from __future__ import annotations

import xml.etree.ElementTree as ET  # nosec B405
from dataclasses import dataclass
from pathlib import Path

from defusedxml.ElementTree import parse as parse_xml

from app.security import redact


@dataclass
class ParsedCase:
    name: str
    suite_name: str
    status: str
    duration_ms: int
    message: str


def parse_junit(path: Path) -> list[ParsedCase]:
    if not path.is_file():
        return []
    root = parse_xml(path).getroot()
    cases: list[ParsedCase] = []

    def walk(node, inherited_name: str) -> None:
        if node.tag != "testsuite":
            return
        suite_name = node.attrib.get("name", inherited_name)
        for child in list(node):
            if child.tag == "testsuite":
                walk(child, suite_name)
            elif child.tag == "testcase":
                _append_case(cases, child, suite_name)

    if root.tag == "testsuite":
        walk(root, "")
    else:
        for child in list(root):
            walk(child, root.attrib.get("name", ""))
    return cases


def _append_case(cases: list[ParsedCase], node: ET.Element, suite_name: str) -> None:
    name = node.attrib.get("name", "unnamed")
    classname = node.attrib.get("classname", suite_name)
    seconds = float(node.attrib.get("time", "0") or 0)
    status = "passed"
    message = ""
    failure = node.find("failure")
    error = node.find("error")
    skipped = node.find("skipped")
    if failure is not None:
        status = "failed"
        message = (failure.attrib.get("message") or failure.text or "").strip()
    elif error is not None:
        status = "error"
        message = (error.attrib.get("message") or error.text or "").strip()
    elif skipped is not None:
        status = "skipped"
        message = (skipped.attrib.get("message") or skipped.text or "").strip()
    cases.append(
        ParsedCase(
            name=name[:200],
            suite_name=(classname or suite_name)[:200],
            status=status,
            duration_ms=max(0, int(seconds * 1000)),
            message=redact(message)[:2000],
        )
    )


def write_junit(path: Path, cases: list[ParsedCase]) -> None:
    suite = ET.Element("testsuite", name="playwright", tests=str(len(cases)))
    for case in cases:
        node = ET.SubElement(
            suite,
            "testcase",
            name=case.name,
            classname=case.suite_name or "playwright",
            time=f"{case.duration_ms / 1000:.3f}",
        )
        if case.status == "failed":
            ET.SubElement(node, "failure", message=case.message).text = case.message
        elif case.status == "error":
            ET.SubElement(node, "error", message=case.message).text = case.message
        elif case.status == "skipped":
            ET.SubElement(node, "skipped", message=case.message)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
