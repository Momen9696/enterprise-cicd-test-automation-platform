import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { Project } from "../types";

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [repository, setRepository] = useState("");
  const [branch, setBranch] = useState("main");

  function load() {
    api<Project[]>("/api/projects").then(setProjects).catch((reason: Error) => setError(reason.message));
  }

  useEffect(load, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/projects", {
        method: "POST",
        body: JSON.stringify({
          name,
          slug,
          repository_url: repository || null,
          default_branch: branch,
          description: "",
        }),
      });
      setName("");
      setSlug("");
      setRepository("");
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create project");
    }
  }

  return (
    <section>
      <div className="split">
        <form className="panel form" onSubmit={create}>
          <header><h2>Register a project</h2></header>
          <label>Name<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
          <label>Slug<input value={slug} onChange={(event) => setSlug(event.target.value)} required /></label>
          <label>Repository URL<input value={repository} onChange={(event) => setRepository(event.target.value)} /></label>
          <label>Default branch<input value={branch} onChange={(event) => setBranch(event.target.value)} /></label>
          <button type="submit">Create project</button>
          {error && <p className="banner warn">{error}</p>}
        </form>
        <section className="panel">
          <header><h2>Projects</h2></header>
          {projects.map((project) => (
            <article key={project.id} className="card">
              <h3>{project.name} {project.is_demo_seed && <em>demo seed</em>}</h3>
              <p>{project.description}</p>
              <p>{project.repository_url || "No repository URL"} · {project.default_branch}</p>
              <p>Environments: {project.environments.map((item) => item.name).join(", ") || "none"}</p>
            </article>
          ))}
        </section>
      </div>
    </section>
  );
}
