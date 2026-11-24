import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ExecutionDetailView } from "../components/ExecutionDetailView";
import type { Execution, TestResult } from "../types";

export function ExecutionDetailPage() {
  const { executionId } = useParams();
  const [execution, setExecution] = useState<Execution | null>(null);
  const [results, setResults] = useState<TestResult[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!executionId) return;
    let stop = false;
    async function load() {
      try {
        const [row, cases] = await Promise.all([
          api<Execution>(`/api/executions/${executionId}`),
          api<TestResult[]>(`/api/executions/${executionId}/results`),
        ]);
        if (!stop) {
          setExecution(row);
          setResults(cases);
        }
        return row.status;
      } catch (reason) {
        if (!stop) setError(reason instanceof Error ? reason.message : "Could not load execution");
        return "error";
      }
    }
    load();
    const timer = window.setInterval(async () => {
      const status = await load();
      if (status !== "queued" && status !== "running") window.clearInterval(timer);
    }, 2000);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [executionId]);

  if (error) return <p className="banner warn">{error}</p>;
  if (!execution) return <p className="empty">Loading execution…</p>;
  return (
    <section>
      <p><Link to="/executions">Back to history</Link></p>
      <ExecutionDetailView execution={execution} results={results} />
    </section>
  );
}
