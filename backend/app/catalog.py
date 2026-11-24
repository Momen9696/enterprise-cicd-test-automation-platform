from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ADAPTERS = ("pytest", "robot", "playwright")
CLASSIFICATIONS = ("smoke", "regression", "pr_validation", "scheduled")
PROVIDERS = ("local", "github_actions", "azure_devops")
RUN_MODES = ("local", "ingest")
STATUSES = ("queued", "running", "passed", "failed", "error", "cancelled")
TRIGGERS = ("manual", "schedule", "pull_request", "push", "webhook")


@dataclass(frozen=True)
class SuiteSpec:
    suite_id: str
    adapter: str
    relative_path: str
    description: str

    def resolve(self, suite_root: Path) -> Path:
        root = suite_root.resolve()
        path = (root / self.relative_path).resolve()
        if path != root and root not in path.parents:
            raise ValueError("Suite path escapes the approved root")
        if not path.is_dir():
            raise ValueError(f"Approved suite directory is missing: {self.suite_id}")
        return path


CATALOG: dict[str, SuiteSpec] = {
    "checkout-pytest": SuiteSpec(
        "checkout-pytest",
        "pytest",
        "checkout-pytest",
        "Checkout totals, SKU rules, and shipping thresholds.",
    ),
    "checkout-failures": SuiteSpec(
        "checkout-failures",
        "pytest",
        "checkout-failures",
        "Intentional failing checkout case used to exercise failure analysis.",
    ),
    "billing-robot": SuiteSpec(
        "billing-robot",
        "robot",
        "billing-robot",
        "Invoice and billing checks written in Robot Framework.",
    ),
    "portal-playwright": SuiteSpec(
        "portal-playwright",
        "playwright",
        "portal-playwright",
        "Browser scenarios for the identity portal, described as data and run by the platform.",
    ),
}


def get_suite(suite_id: str) -> SuiteSpec:
    try:
        return CATALOG[suite_id]
    except KeyError as exc:
        raise ValueError(f"Unknown suite '{suite_id}'") from exc


def marker_for(classification: str, adapter: str) -> str | None:
    if classification == "smoke" or classification == "pr_validation":
        return "smoke"
    if classification == "regression":
        return "regression"
    if classification == "scheduled":
        return None
    raise ValueError(f"Unsupported classification '{classification}'")
