import { useQuery } from "@tanstack/react-query";
import { api } from "./lib/api";
import { DocumentPanel } from "./components/DocumentPanel";
import { ChatPanel } from "./components/ChatPanel";

export default function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✦</span>
          <div>
            <h1 className="text-lg font-semibold text-slate-100">Lumen</h1>
            <p className="text-xs text-slate-500">Grounded answers over your documents</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span
            className={`h-2 w-2 rounded-full ${
              health.data?.llm_configured ? "bg-emerald-400" : "bg-amber-400"
            }`}
          />
          {health.data ? health.data.model : "connecting…"}
        </div>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-[320px_1fr]">
        <DocumentPanel />
        <ChatPanel llmReady={health.data?.llm_configured ?? false} />
      </main>
    </div>
  );
}
