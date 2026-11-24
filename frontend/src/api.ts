const STORAGE_KEY = "platform.apiKey";

export function apiKey(): string {
  return localStorage.getItem(STORAGE_KEY) || "local-operator-key";
}

export function setApiKey(value: string): void {
  localStorage.setItem(STORAGE_KEY, value.trim());
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  headers.set("X-API-Key", apiKey());
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    } catch {
      detail = response.statusText;
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  const type = response.headers.get("content-type") || "";
  if (type.includes("application/json")) return response.json() as Promise<T>;
  return (await response.text()) as T;
}

export async function download(path: string, filename: string): Promise<void> {
  const headers = new Headers();
  headers.set("X-API-Key", apiKey());
  const response = await fetch(path, { headers });
  if (!response.ok) throw new Error(`Download failed (${response.status})`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
