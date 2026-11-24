import { useEffect, useState } from "react";
import { api, download } from "../api";
import { buildQuery } from "../format";
import { FilterBar } from "../components/FilterBar";
import { emptyFilters, type Filters, type Pipeline, type Project, type Summary } from "../types";

export function ReportsPage() {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [projects, setProjects] = useState<Project[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Project[]>("/api/projects"), api<Pipeline[]>("/api/pipelines")]).then(([projectRows, pipelineRows]) => {
      setProjects(projectRows);
      setPipelines(pipelineRows);
    });
  }, []);

  useEffect(() => {
    api<Summary>(`/api/analytics/summary?${buildQuery(filters)}`)
      .then(setSummary)
      .catch((reason: Error) => setError(reason.message));
  }, [filters]);

  async function save(format: string) {
    try {
      await download(`/api/reports/aggregate?${buildQuery(filters)}&format=${format}`, `aggregate-report.${format === "md" ? "md" : format}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Download failed");
    }
  }

  return (
    <section>
      <FilterBar filters={filters} projects={projects} pipelines={pipelines} onChange={setFilters} />
      {error && <p className="banner warn">{error}</p>}
      {summary && (
        <section className="panel">
          <header><h2>Aggregate report</h2><p>Source: {summary.source}</p></header>
          <div className="kpis compact">
            <article><span>Runs</span><strong>{summary.total_runs}</strong></article>
            <article><span>Success</span><strong>{summary.success_rate}%</strong></article>
            <article><span>Test pass rate</span><strong>{summary.test_pass_rate}%</strong></article>
          </div>
          <div className="actions">
            <button type="button" onClick={() => save("html")}>Download HTML</button>
            <button type="button" onClick={() => save("csv")}>Download CSV</button>
            <button type="button" onClick={() => save("md")}>Download Markdown</button>
          </div>
        </section>
      )}
    </section>
  );
}
