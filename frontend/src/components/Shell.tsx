import { NavLink, Outlet } from "react-router-dom";
import { FormEvent, useEffect, useState } from "react";
import { apiKey, setApiKey } from "../api";

const links = [
  ["/", "Overview"],
  ["/projects", "Projects"],
  ["/pipelines", "Pipelines"],
  ["/executions", "Executions"],
  ["/reports", "Reports"],
  ["/templates", "Templates"],
];

export function Shell() {
  const [health, setHealth] = useState("checking");
  const [key, setKey] = useState(apiKey());

  useEffect(() => {
    fetch("/health")
      .then((response) => setHealth(response.ok ? "online" : "unreachable"))
      .catch(() => setHealth("unreachable"));
  }, []);

  function saveKey(event: FormEvent) {
    event.preventDefault();
    setApiKey(key);
    window.location.reload();
  }

  return (
    <div className="shell">
      <aside className="rail">
        <div>
          <p className="mark">Northline QA</p>
          <strong>Test platform</strong>
        </div>
        <nav>
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>
              {label}
            </NavLink>
          ))}
        </nav>
        <form onSubmit={saveKey} className="key-form">
          <label>
            API key
            <input value={key} onChange={(event) => setKey(event.target.value)} />
          </label>
          <button type="submit">Save key</button>
        </form>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Execution control</p>
            <h1>CI/CD test automation</h1>
          </div>
          <span className={`health health-${health}`}>{health}</span>
        </header>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
