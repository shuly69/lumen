import type { DocumentList, DocumentSummary, Health } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetch("/api/health").then(json<Health>),

  listDocuments: () => fetch("/api/documents").then(json<DocumentList>),

  addDocument: (title: string, content: string) =>
    fetch("/api/documents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content }),
    }).then(json<DocumentSummary>),

  deleteDocument: async (id: string) => {
    const res = await fetch(`/api/documents/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  },
};
