import type { Execution, TestResult } from "../types";
import { formatDuration, formatWhen } from "../format";

export function ExecutionDetailView({ execution, results }: { execution: Execution; results: TestResult[] }) {
  const failed = results.filter((result) => result.status === "failed" || result.status === "error");
  return (
    <section>
      <header className="detail-head">
        <div>
          <p className="eyebrow">{execution.project_name}</p>
          <h2>{execution.pipeline_name}</h2>
        </div>
        <span className={`status status-${execution.status}`}>{execution.status}</span>
      </header>
      <div className="kpis compact">
        <article><span>Duration</span><strong>{formatDuration(execution.duration_ms)}</strong></article>
        <article><span>Passed</span><strong>{execution.passed_tests}</strong></article>
        <article><span>Failed</span><strong>{execution.failed_tests}</strong></article>
        <article><span>Skipped</span><strong>{execution.skipped_tests}</strong></article>
      </div>
      <dl className="facts">
        <div><dt>Branch</dt><dd>{execution.branch}</dd></div>
        <div><dt>Environment</dt><dd>{execution.environment_name}</dd></div>
        <div><dt>Trigger</dt><dd>{execution.trigger}</dd></div>
        <div><dt>Provider</dt><dd>{execution.provider}</dd></div>
        <div><dt>Started</dt><dd>{formatWhen(execution.started_at)}</dd></div>
        <div><dt>Source</dt><dd>{execution.is_demo_seed ? "Demo seed" : execution.triggered_by}</dd></div>
      </dl>
      {execution.error_message && <p className="banner warn">{execution.error_message}</p>}
      <section className="panel">
        <header><h2>Failed tests</h2></header>
        {failed.length === 0 ? <p className="empty">No failed tests were stored for this run.</p> : (
          <ul className="failures">
            {failed.map((result) => (
              <li key={result.id}>
                <div><strong>{result.name}</strong><p>{result.suite_name}</p></div>
                <small>{result.message || "No message"}</small>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="panel">
        <header><h2>All results</h2></header>
        <table>
          <thead><tr><th>Test</th><th>Status</th><th>Duration</th><th>Message</th></tr></thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.id}>
                <td>{result.name}</td>
                <td><span className={`status status-${result.status}`}>{result.status}</span></td>
                <td>{formatDuration(result.duration_ms)}</td>
                <td>{result.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}
