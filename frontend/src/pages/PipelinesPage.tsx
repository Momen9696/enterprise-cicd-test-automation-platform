import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Pipeline, Project } from "../types";

export function PipelinesPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    project_id: "",
    environment_id: "",
    name: "",
    provider: "local",
    template_key: "smoke",
    suite_id: "checkout-pytest",
    classification: "smoke",
    branch_pattern: "*",
    run_mode: "local",
  });

  function load() {
    Promise.all([api<Project[]>("/api/projects"), api<Pipeline[]>("/api/pipelines")]).then(([projectRows, pipelineRows]) => {
      setProjects(projectRows);
      setPipelines(pipelineRows);
    });
  }

  useEffect(load, []);

  const selected = projects.find((project) => String(project.id) === form.project_id);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/pipelines", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          project_id: Number(form.project_id),
          environment_id: form.environment_id ? Number(form.environment_id) : null,
        }),
      });
      setMessage("Pipeline saved.");
      load();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Could not save pipeline");
    }
  }

  async function run(pipeline: Pipeline) {
    try {
      const execution = await api<{ id: number; status: string }>("/api/executions", {
        method: "POST",
        body: JSON.stringify({ pipeline_id: pipeline.id, trigger: pipeline.classification === "scheduled" ? "schedule" : "manual" }),
      });
      setMessage(`Execution ${execution.id} is ${execution.status}.`);
      load();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Run failed");
    }
  }

  return (
    <section className="split">
      <form className="panel form" onSubmit={create}>
        <header><h2>Pipeline configuration</h2></header>
        <label>Project
          <select value={form.project_id} onChange={(event) => setForm({ ...form, project_id: event.target.value, environment_id: "" })} required>
            <option value="">Select</option>
            {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
        </label>
        <label>Environment
          <select value={form.environment_id} onChange={(event) => setForm({ ...form, environment_id: event.target.value })}>
            <option value="">None</option>
            {selected?.environments.map((environment) => (
              <option key={environment.id} value={environment.id}>{environment.name}</option>
            ))}
          </select>
        </label>
        <label>Name<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></label>
        <label>Provider
          <select value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })}>
            <option value="local">local</option>
            <option value="github_actions">github_actions</option>
            <option value="azure_devops">azure_devops</option>
          </select>
        </label>
        <label>Suite
          <select value={form.suite_id} onChange={(event) => setForm({ ...form, suite_id: event.target.value })}>
            <option value="checkout-pytest">checkout-pytest</option>
            <option value="checkout-failures">checkout-failures</option>
            <option value="billing-robot">billing-robot</option>
            <option value="portal-playwright">portal-playwright</option>
          </select>
        </label>
        <label>Classification
          <select value={form.classification} onChange={(event) => setForm({ ...form, classification: event.target.value })}>
            <option value="smoke">smoke</option>
            <option value="regression">regression</option>
            <option value="pr_validation">pr_validation</option>
            <option value="scheduled">scheduled</option>
          </select>
        </label>
        <label>Template key<input value={form.template_key} onChange={(event) => setForm({ ...form, template_key: event.target.value })} /></label>
        <label>Branch pattern<input value={form.branch_pattern} onChange={(event) => setForm({ ...form, branch_pattern: event.target.value })} /></label>
        <label>Run mode
          <select value={form.run_mode} onChange={(event) => setForm({ ...form, run_mode: event.target.value })}>
            <option value="local">local</option>
            <option value="ingest">ingest</option>
          </select>
        </label>
        <button type="submit">Save pipeline</button>
        {message && <p className="banner">{message}</p>}
      </form>
      <section className="panel">
        <header><h2>Configured pipelines</h2></header>
        <table>
          <thead><tr><th>Name</th><th>Suite</th><th>Class</th><th>Mode</th><th>Latest</th><th></th></tr></thead>
          <tbody>
            {pipelines.map((pipeline) => (
              <tr key={pipeline.id}>
                <td>{pipeline.name}{pipeline.is_demo_seed ? " · demo" : ""}<br /><small>{pipeline.project_name}</small></td>
                <td>{pipeline.adapter}</td>
                <td>{pipeline.classification}</td>
                <td>{pipeline.run_mode}</td>
                <td>{pipeline.latest_status || "—"}</td>
                <td><button type="button" onClick={() => run(pipeline)} disabled={!pipeline.enabled}>Run</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}
