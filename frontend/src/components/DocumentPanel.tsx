import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { SAMPLE_DOCS } from "../lib/samples";

export function DocumentPanel() {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [open, setOpen] = useState(false);

  const docs = useQuery({ queryKey: ["documents"], queryFn: api.listDocuments });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["documents"] });

  const add = useMutation({
    mutationFn: () => api.addDocument(title.trim(), content.trim()),
    onSuccess: () => {
      setTitle("");
      setContent("");
      setOpen(false);
      invalidate();
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: invalidate,
  });

  const seed = useMutation({
    mutationFn: async () => {
      for (const d of SAMPLE_DOCS) await api.addDocument(d.title, d.content);
    },
    onSuccess: invalidate,
  });

  const documents = docs.data?.documents ?? [];

  return (
    <aside className="flex h-full flex-col gap-4 border-r border-slate-800 bg-slate-950/40 p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-slate-300 uppercase">Corpus</h2>
          <p className="text-xs text-slate-500">
            {documents.length} docs · {docs.data?.total_chunks ?? 0} chunks
          </p>
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="rounded-lg bg-indigo-500 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-400"
        >
          {open ? "Cancel" : "+ Add"}
        </button>
      </div>

      {open && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim() && content.trim()) add.mutate();
          }}
          className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-3"
        >
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Document title"
            className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Paste text to index…"
            rows={6}
            className="resize-none rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={add.isPending || !title.trim() || !content.trim()}
            className="rounded-md bg-indigo-500 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-400 disabled:opacity-40"
          >
            {add.isPending ? "Indexing…" : "Index document"}
          </button>
          {add.isError && <p className="text-xs text-rose-400">{String(add.error)}</p>}
        </form>
      )}

      <div className="flex-1 space-y-2 overflow-y-auto">
        {documents.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-800 p-4 text-center text-sm text-slate-500">
            <p>No documents indexed yet.</p>
            <button
              onClick={() => seed.mutate()}
              disabled={seed.isPending}
              className="mt-3 rounded-md border border-slate-700 px-3 py-1.5 text-xs text-indigo-300 transition hover:border-indigo-500 disabled:opacity-40"
            >
              {seed.isPending ? "Loading…" : "Load sample documents"}
            </button>
          </div>
        )}

        {documents.map((d) => (
          <div
            key={d.id}
            className="group flex items-start justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/50 p-3"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-200">{d.title}</p>
              <p className="text-xs text-slate-500">
                {d.chunk_count} chunks · {d.char_count.toLocaleString()} chars
              </p>
            </div>
            <button
              onClick={() => remove.mutate(d.id)}
              className="text-slate-600 opacity-0 transition group-hover:opacity-100 hover:text-rose-400"
              title="Delete"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
