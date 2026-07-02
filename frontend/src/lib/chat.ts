import type { Citation } from "./types";

export interface ChatHandlers {
  onSources: (citations: Citation[]) => void;
  onToken: (text: string) => void;
  onError: (message: string) => void;
  onDone: () => void;
}

/**
 * Stream a RAG answer over Server-Sent Events.
 *
 * EventSource only speaks GET, so we POST with fetch and parse the SSE frames off
 * the response body ourselves. Frames are separated by a blank line and carry an
 * `event:` type plus a JSON `data:` payload.
 */
export async function streamChat(
  question: string,
  handlers: ChatHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });

  if (!res.ok || !res.body) {
    handlers.onError(`Request failed (${res.status})`);
    return;
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    // Normalize CRLF → LF: sse-starlette separates frames with `\r\n\r\n`.
    // Stripping CR (rather than replacing `\r\n`) is robust to a split across reads.
    buffer += value.replace(/\r/g, "");

    // Dispatch every complete frame (terminated by a blank line).
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      dispatchFrame(frame, handlers);
    }
  }
  handlers.onDone();
}

function dispatchFrame(frame: string, handlers: ChatHandlers): void {
  let event = "message";
  let data = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return;

  const payload = JSON.parse(data);
  switch (event) {
    case "sources":
      handlers.onSources(payload.citations);
      break;
    case "token":
      handlers.onToken(payload.text);
      break;
    case "error":
      handlers.onError(payload.message);
      break;
  }
}
