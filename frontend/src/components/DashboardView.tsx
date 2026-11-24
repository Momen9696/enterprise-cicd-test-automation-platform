import type { FailureStat, ProjectStat, Summary, TrendPoint, Execution } from "../types";
import { formatDuration, formatWhen } from "../format";
import { Link } from "react-router-dom";

export function DashboardView({
  summary,
  trends,
  projects,
  failures,
  activity,
}: {
  summary: Summary;
  trends: TrendPoint[];
  projects: ProjectStat[];
  failures: FailureStat[];
  activity: Execution[];
}) {
  const max = Math.max(1, ...trends.map((point) => point.passed + point.failed + point.error));
  return (
    <section>
      {summary.demo_seed_runs > 0 && (
        <p className="banner">
          Demo seed is included: {summary.demo_seed_runs} synthetic runs are stored in the database and labeled on each row.
          Clear “Include demo seed” to see live runs only.
        </p>
      )}
      <div className="kpis">
        <article data-testid="kpi-total"><span>Total runs</span><strong>{summary.total_runs}</strong></article>
        <article data-testid="kpi-passed"><span>Passed</span><strong>{summary.passed_runs}</strong></article>
        <article data-testid="kpi-failed"><span>Failed</span><strong>{summary.failed_runs}</strong></article>
        <article data-testid="kpi-running"><span>Running</span><strong>{summary.running_runs}</strong></article>
        <article><span>Success rate</span><strong>{summary.success_rate}%</strong></article>
        <article><span>Average duration</span><strong>{formatDuration(summary.average_duration_ms)}</strong></article>
      </div>
      <div className="split">
        <section className="panel">
          <header><h2>Pass / fail trend</h2><p>Counts per day from stored executions.</p></header>
          {trends.length === 0 ? <p className="empty">No executions in this filter.</p> : (
            <div className="trend" data-testid="trend">
              {trends.map((point) => (
                <div key={point.date} className="bar">
                  <div className="stack" style={{ height: `${((point.passed + point.failed + point.error) / max) * 100}%` }}>
                    <span className="seg failed" style={{ flex: point.failed + point.error }} />
                    <span className="seg passed" style={{ flex: point.passed }} />
                  </div>
                  <small>{point.date.slice(5)}</small>
                </div>
              ))}
            </div>
          )}
        </section>
        <section className="panel">
          <header><h2>Repeated failures</h2><p>Grouped from stored failed and error results.</p></header>
          {failures.length === 0 ? <p className="empty">No failed tests in this filter.</p> : (
            <ul className="failures">
              {failures.map((item) => (
                <li key={`${item.project_name}-${item.name}`}>
                  <div>
                    <strong>{item.name}</strong>
                    <p>{item.project_name} · {item.failures} failed</p>
                  </div>
                  <small>{item.last_message || "No message"}</small>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      <section className="panel">
        <header><h2>Projects</h2></header>
        <table>
          <thead>
            <tr><th>Project</th><th>Runs</th><th>Passed</th><th>Failed</th><th>Success</th><th>Avg duration</th></tr>
          </thead>
          <tbody>
            {projects.map((project) => (
              <tr key={project.project_id}>
                <td>{project.project_name}</td>
                <td>{project.runs}</td>
                <td>{project.passed}</td>
                <td>{project.failed}</td>
                <td>{project.success_rate}%</td>
                <td>{formatDuration(project.average_duration_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <header><h2>Recent activity</h2></header>
        <table>
          <thead>
            <tr><th>When</th><th>Project</th><th>Pipeline</th><th>Branch</th><th>Env</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {activity.map((item) => (
              <tr key={item.id}>
                <td>{formatWhen(item.started_at)}</td>
                <td>{item.project_name}</td>
                <td>{item.pipeline_name}{item.is_demo_seed ? " · demo" : ""}</td>
                <td>{item.branch}</td>
                <td>{item.environment_name}</td>
                <td><span className={`status status-${item.status}`}>{item.status}</span></td>
                <td><Link to={`/executions/${item.id}`}>Open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}
