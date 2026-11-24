import { useEffect, useState } from "react";
import { api } from "../api";
import type { TemplateItem } from "../types";

export function TemplatesPage() {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<TemplateItem[]>("/api/providers/templates")
      .then(setTemplates)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  async function open(item: TemplateItem) {
    try {
      const payload = await api<{ content: string }>(`/api/providers/templates/${item.provider}/${item.filename}`);
      setSelected(payload.content);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not read template");
    }
  }

  return (
    <section className="split">
      <section className="panel">
        <header><h2>Template library</h2><p>GitHub Actions and Azure DevOps examples. They are validated, not executed by the API.</p></header>
        {error && <p className="banner warn">{error}</p>}
        <table>
          <thead><tr><th>Provider</th><th>File</th><th>Valid</th><th></th></tr></thead>
          <tbody>
            {templates.map((item) => (
              <tr key={`${item.provider}-${item.filename}`}>
                <td>{item.provider}</td>
                <td>{item.filename}</td>
                <td>{item.valid ? "yes" : item.errors.join("; ")}</td>
                <td><button type="button" onClick={() => open(item)}>View</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="panel">
        <header><h2>YAML</h2></header>
        <pre>{selected || "Select a template to view its YAML."}</pre>
      </section>
    </section>
  );
}
