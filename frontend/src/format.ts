import type { Filters } from "./types";

export function buildQuery(filters: Filters, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams();
  if (filters.project_id) params.set("project_id", filters.project_id);
  if (filters.pipeline_id) params.set("pipeline_id", filters.pipeline_id);
  if (filters.branch.trim()) params.set("branch", filters.branch.trim());
  if (filters.environment) params.set("environment", filters.environment);
  if (filters.status) params.set("status", filters.status);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  params.set("include_demo", filters.include_demo ? "true" : "false");
  for (const [key, value] of Object.entries(extra)) params.set(key, value);
  return params.toString();
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes}m ${rest}s`;
}

export function formatWhen(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value.endsWith("Z") || value.includes("+") ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
