import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { streamChat } from "../lib/chat";
import type { Citation } from "../lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  error?: boolean;
}

export function ChatPanel({ llmReady }: { llmReady: boolean }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () =>
    requestAnimationFrame(() =>
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }),
    );

  // Update the last (assistant) message immutably.
  const patchLast = (patch: (m: Message) => Message) =>
    setMessages((prev) => prev.map((m, i) => (i === prev.length - 1 ? patch(m) : m)));

  async function send() {
    const question = input.trim();
    if (!question || streaming) return;

    setInput("");
    setStreaming(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);
    scrollToBottom();

    await streamChat(question, {
      onSources: (citations) => patchLast((m) => ({ ...m, citations })),
      onToken: (text) => {
        patchLast((m) => ({ ...m, content: m.content + text }));
        scrollToBottom();
      },
      onError: (message) => patchLast((m) => ({ ...m, content: message, error: true })),
      onDone: () => setStreaming(false),
    });
  }

  return (
    <section className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
        {messages.length === 0 && <EmptyState llmReady={llmReady} />}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} streaming={streaming && i === messages.length - 1} />
        ))}
      </div>

      <div className="border-t border-slate-800 bg-slate-950/60 px-6 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="flex items-end gap-3"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            placeholder="Ask a question about your documents…"
            className="max-h-40 flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-xl bg-indigo-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:opacity-40"
          >
            {streaming ? "…" : "Ask"}
          </button>
        </form>
        <p className="mt-2 text-xs text-slate-600">
          Answers are grounded in your indexed documents and cite their sources.
        </p>
      </div>
    </section>
  );
}

function MessageBubble({ message, streaming }: { message: Message; streaming: boolean }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-indigo-500/90 px-4 py-2.5 text-sm text-white">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        className={`max-w-[85%] rounded-2xl rounded-bl-sm border px-4 py-3 text-sm ${
          message.error
            ? "border-rose-500/40 bg-rose-500/10 text-rose-200"
            : "border-slate-800 bg-slate-900/70 text-slate-200"
        }`}
      >
        <div className={`markdown ${streaming ? "caret" : ""}`}>
          <ReactMarkdown>{message.content || (streaming ? "" : "…")}</ReactMarkdown>
        </div>
      </div>
      {message.citations && message.citations.length > 0 && (
        <div className="flex max-w-[85%] flex-wrap gap-2">
          {message.citations.map((c) => (
            <div
              key={c.marker}
              className="group relative rounded-lg border border-slate-800 bg-slate-900/50 px-2.5 py-1 text-xs text-slate-400"
            >
              <span className="font-semibold text-indigo-300">[{c.marker}]</span>{" "}
              {c.document_title}
              <div className="pointer-events-none absolute bottom-full left-0 z-10 mb-2 hidden w-72 rounded-lg border border-slate-700 bg-slate-950 p-3 text-xs leading-relaxed text-slate-300 shadow-xl group-hover:block">
                {c.snippet}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EmptyState({ llmReady }: { llmReady: boolean }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
      <div className="mb-3 text-4xl">✦</div>
      <h3 className="text-lg font-medium text-slate-300">Ask your documents anything</h3>
      <p className="mt-1 max-w-sm text-sm">
        Lumen retrieves the most relevant passages and asks Claude to answer using only those
        sources — with citations you can verify.
      </p>
      {!llmReady && (
        <p className="mt-4 rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
          No API key configured on the server — set <code>LUMEN_ANTHROPIC_API_KEY</code> to enable
          answers.
        </p>
      )}
    </div>
  );
}
