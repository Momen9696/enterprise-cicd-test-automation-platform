import type { Filters, Pipeline, Project } from "../types";

type Props = {
  filters: Filters;
  projects: Project[];
  pipelines: Pipeline[];
  onChange: (filters: Filters) => void;
};

export function FilterBar({ filters, projects, pipelines, onChange }: Props) {
  function update(partial: Partial<Filters>) {
    onChange({ ...filters, ...partial });
  }

  return (
    <form className="filters" onSubmit={(event) => event.preventDefault()}>
      <label>
        Project
        <select value={filters.project_id} onChange={(event) => update({ project_id: event.target.value })}>
          <option value="">All projects</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Pipeline
        <select value={filters.pipeline_id} onChange={(event) => update({ pipeline_id: event.target.value })}>
          <option value="">All pipelines</option>
          {pipelines.map((pipeline) => (
            <option key={pipeline.id} value={pipeline.id}>
              {pipeline.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Branch
        <input value={filters.branch} onChange={(event) => update({ branch: event.target.value })} placeholder="main" />
      </label>
      <label>
        Environment
        <select value={filters.environment} onChange={(event) => update({ environment: event.target.value })}>
          <option value="">All environments</option>
          <option value="dev">dev</option>
          <option value="staging">staging</option>
          <option value="qa">qa</option>
        </select>
      </label>
      <label>
        Status
        <select value={filters.status} onChange={(event) => update({ status: event.target.value })}>
          <option value="">Any status</option>
          {["passed", "failed", "running", "error", "cancelled", "queued"].map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </label>
      <label>
        From
        <input type="date" value={filters.date_from} onChange={(event) => update({ date_from: event.target.value })} />
      </label>
      <label>
        To
        <input type="date" value={filters.date_to} onChange={(event) => update({ date_to: event.target.value })} />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={filters.include_demo}
          onChange={(event) => update({ include_demo: event.target.checked })}
        />
        Include demo seed
      </label>
    </form>
  );
}
