import { useEffect, useState } from "react";
import { api } from "../api";
import { buildQuery } from "../format";
import { DashboardView } from "../components/DashboardView";
import { FilterBar } from "../components/FilterBar";
import { emptyFilters, type Execution, type FailureStat, type Filters, type Pipeline, type Project, type ProjectStat, type Summary, type TrendPoint } from "../types";

export function DashboardPage() {
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [projects, setProjects] = useState<Project[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [stats, setStats] = useState<ProjectStat[]>([]);
  const [failures, setFailures] = useState<FailureStat[]>([]);
  const [activity, setActivity] = useState<Execution[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Project[]>("/api/projects"), api<Pipeline[]>("/api/pipelines")])
      .then(([projectRows, pipelineRows]) => {
        setProjects(projectRows);
        setPipelines(pipelineRows);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  useEffect(() => {
    const query = buildQuery(filters);
    Promise.all([
      api<Summary>(`/api/analytics/summary?${query}`),
      api<TrendPoint[]>(`/api/analytics/trends?${query}`),
      api<ProjectStat[]>(`/api/analytics/projects?${query}`),
      api<FailureStat[]>(`/api/analytics/failures?${query}`),
      api<{ items: Execution[] }>(`/api/executions?${query}&limit=8`),
    ])
      .then(([summaryRow, trendRows, projectRows, failureRows, executions]) => {
        setSummary(summaryRow);
        setTrends(trendRows);
        setStats(projectRows);
        setFailures(failureRows);
        setActivity(executions.items);
        setError("");
      })
      .catch((reason: Error) => setError(reason.message));
  }, [filters]);

  return (
    <>
      <FilterBar filters={filters} projects={projects} pipelines={pipelines} onChange={setFilters} />
      {error && <p className="banner warn">{error}</p>}
      {summary && (
        <DashboardView summary={summary} trends={trends} projects={stats} failures={failures} activity={activity} />
      )}
    </>
  );
}
