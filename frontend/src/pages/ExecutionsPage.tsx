import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { buildQuery, formatDuration, formatWhen } from "../format";
import { FilterBar } from "../components/FilterBar";
import { emptyFilters, type Execution, type Filters, type Pipeline, type Project } from "../types";

export function ExecutionsPage() {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [projects, setProjects] = useState<Project[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [rows, setRows] = useState<Execution[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Project[]>("/api/projects"), api<Pipeline[]>("/api/pipelines")]).then(([projectRows, pipelineRows]) => {
      setProjects(projectRows);
      setPipelines(pipelineRows);
    });
  }, []);

  useEffect(() => {
    api<{ items: Execution[]; total: number }>(`/api/executions?${buildQuery(filters)}&limit=50`)
      .then((page) => {
        setRows(page.items);
        setTotal(page.total);
      })
      .catch((reason: Error) => setError(reason.message));
  }, [filters]);

  return (
    <section>
      <FilterBar filters={filters} projects={projects} pipelines={pipelines} onChange={setFilters} />
      {error && <p className="banner warn">{error}</p>}
      <section className="panel">
        <header><h2>Execution history</h2><p>{total} stored runs</p></header>
        <table>
          <thead>
            <tr><th>When</th><th>Project</th><th>Pipeline</th><th>Branch</th><th>Env</th><th>Status</th><th>Duration</th><th>Failed</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{formatWhen(row.started_at)}</td>
                <td>{row.project_name}</td>
                <td>{row.pipeline_name}{row.is_demo_seed ? " · demo" : ""}</td>
                <td>{row.branch}</td>
                <td>{row.environment_name}</td>
                <td><span className={`status status-${row.status}`}>{row.status}</span></td>
                <td>{formatDuration(row.duration_ms)}</td>
                <td>{row.failed_tests}</td>
                <td><Link to={`/executions/${row.id}`}>Details</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}
