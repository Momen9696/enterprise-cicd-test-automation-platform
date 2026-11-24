import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { DashboardView } from "../components/DashboardView";
import { ExecutionDetailView } from "../components/ExecutionDetailView";
import { buildQuery, formatDuration } from "../format";
import { emptyFilters, type Execution, type Summary } from "../types";

const summary: Summary = {
  total_runs: 36,
  passed_runs: 25,
  failed_runs: 5,
  error_runs: 3,
  running_runs: 1,
  cancelled_runs: 2,
  average_duration_ms: 42000,
  success_rate: 75.8,
  test_pass_rate: 80,
  demo_seed_runs: 36,
  source: "database",
};

const execution: Execution = {
  id: 7,
  project_id: 1,
  project_name: "Harbor Checkout",
  pipeline_id: 2,
  pipeline_name: "Pytest regression",
  environment_name: "staging",
  status: "failed",
  trigger: "manual",
  branch: "main",
  commit_sha: null,
  started_at: "2026-11-20T10:00:00",
  finished_at: "2026-11-20T10:01:00",
  duration_ms: 60000,
  total_tests: 4,
  passed_tests: 3,
  failed_tests: 1,
  skipped_tests: 0,
  error_message: null,
  triggered_by: "demo-seed",
  is_demo_seed: true,
  provider: "local",
  classification: "regression",
};

describe("filters", () => {
  it("builds the analytics query from the selected filters", () => {
    const query = buildQuery({
      ...emptyFilters,
      project_id: "3",
      branch: "main",
      status: "failed",
      include_demo: false,
    });
    expect(query).toContain("project_id=3");
    expect(query).toContain("branch=main");
    expect(query).toContain("status=failed");
    expect(query).toContain("include_demo=false");
  });

  it("formats durations from stored milliseconds", () => {
    expect(formatDuration(null)).toBe("—");
    expect(formatDuration(42000)).toBe("42.0 s");
  });
});

describe("dashboard", () => {
  it("renders persisted summary figures", () => {
    render(
      <MemoryRouter>
        <DashboardView summary={summary} trends={[{ date: "2026-11-20", passed: 4, failed: 1, error: 0 }]} projects={[{ project_id: 1, project_name: "Harbor Checkout", runs: 12, passed: 9, failed: 2, average_duration_ms: 30000, success_rate: 81.8 }]} failures={[{ name: "test_tax_rounding", suite_name: "checkout", failures: 3, last_message: "rounded tax did not match", last_seen: "2026-11-20T10:00:00", project_name: "Harbor Checkout" }]} activity={[execution]} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId("kpi-total")).toHaveTextContent("36");
    expect(screen.getByTestId("kpi-passed")).toHaveTextContent("25");
    expect(screen.getByTestId("kpi-failed")).toHaveTextContent("5");
    expect(screen.getByTestId("kpi-running")).toHaveTextContent("1");
    expect(screen.getByText("test_tax_rounding")).toBeInTheDocument();
    expect(screen.getByText(/Demo seed is included/)).toBeInTheDocument();
  });
});

describe("execution detail", () => {
  it("shows the failed test stored for the run", () => {
    render(
      <ExecutionDetailView
        execution={execution}
        results={[
          { id: 1, name: "test_cart_subtotal", suite_name: "checkout", status: "passed", duration_ms: 10, message: "", classification: "regression" },
          { id: 2, name: "test_tax_rounding", suite_name: "checkout", status: "failed", duration_ms: 15, message: "rounded tax did not match", classification: "regression" },
        ]}
      />,
    );
    expect(screen.getAllByText("test_tax_rounding")).toHaveLength(2);
    expect(screen.getAllByText("rounded tax did not match")).toHaveLength(2);
    expect(screen.getByText("Demo seed")).toBeInTheDocument();
  });
});

describe("api client", () => {
  it("sends the stored API key and surfaces error details", async () => {
    localStorage.setItem("platform.apiKey", "viewer-key");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: { get: () => "application/json" },
      json: async () => ({ ok: true }),
    });
    vi.stubGlobal("fetch", fetchMock);
    await api("/api/projects");
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("X-API-Key")).toBe("viewer-key");
    fetchMock.mockResolvedValue({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      headers: { get: () => "application/json" },
      json: async () => ({ detail: "Operator API key required" }),
    });
    await expect(api("/api/projects", { method: "POST", body: "{}" })).rejects.toThrow("Operator API key required");
  });
});
