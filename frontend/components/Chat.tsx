"use client";

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Source, chatUrl } from "@/lib/api";

interface DoneMeta {
  citations: number[];
  invalid_citations: number[];
  model: string;
}

const EXAMPLE_QUESTIONS = [
  "What are the biggest risk factors mentioned in the latest 10-K?",
  "How did revenue develop in the most recent quarter, and why?",
  "What does management say about competition?",
];

/** Turn plain [n] citations into links targeting the source panel. */
function linkCitations(markdown: string): string {
  return markdown.replace(/\[(\d{1,2})\]/g, "[[$1]](#source-$1)");
}

export default function Chat({ ticker }: { ticker: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [meta, setMeta] = useState<DoneMeta | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const sessionId = useRef<number | null>(null);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;
    setStreaming(true);
    setAnswer("");
    setSources([]);
    setMeta(null);
    setError(null);
    setActiveSource(null);

    try {
      const response = await fetch(chatUrl(ticker), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmed,
          session_id: sessionId.current,
        }),
      });
      if (!response.ok || !response.body) {
        throw new Error(`API error ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) !== -1) {
          const raw = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const eventLine = raw.split("\n").find((l) => l.startsWith("event: "));
          const dataLine = raw.split("\n").find((l) => l.startsWith("data: "));
          if (!eventLine || !dataLine) continue;
          const event = eventLine.slice(7);
          const data = JSON.parse(dataLine.slice(6));

          if (event === "sources") {
            setSources(data.sources);
            sessionId.current = data.session_id;
          } else if (event === "delta") {
            setAnswer((previous) => previous + data.text);
          } else if (event === "done") {
            setMeta(data);
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setStreaming(false);
    }
  }

  function onCitationClick(event: React.MouseEvent) {
    const target = event.target as HTMLElement;
    const anchor = target.closest("a");
    const href = anchor?.getAttribute("href");
    if (href?.startsWith("#source-")) {
      event.preventDefault();
      const index = Number(href.slice("#source-".length));
      setActiveSource(index);
      document
        .getElementById(`source-${index}`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            ask(question);
          }}
          className="flex gap-2"
        >
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder={`Ask about ${ticker}'s filings…`}
            className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-600"
          />
          <button
            type="submit"
            disabled={streaming || question.trim().length < 3}
            className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-40"
          >
            {streaming ? "Thinking…" : "Ask"}
          </button>
        </form>

        {!answer && !streaming && (
          <div className="mt-4 space-y-2">
            {EXAMPLE_QUESTIONS.map((example) => (
              <button
                key={example}
                onClick={() => {
                  setQuestion(example);
                  ask(example);
                }}
                className="block w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-600 hover:border-emerald-600 hover:text-slate-900"
              >
                {example}
              </button>
            ))}
          </div>
        )}

        {error && (
          <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {(answer || streaming) && (
          <div
            onClick={onCitationClick}
            className="prose prose-sm prose-slate mt-6 max-w-none rounded-lg border border-slate-200 bg-white p-5 [&_a[href^='#source-']]:rounded [&_a[href^='#source-']]:bg-emerald-100 [&_a[href^='#source-']]:px-1 [&_a[href^='#source-']]:font-medium [&_a[href^='#source-']]:text-emerald-800 [&_a[href^='#source-']]:no-underline [&_table]:text-xs"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {linkCitations(answer)}
            </ReactMarkdown>
            {streaming && <span className="animate-pulse text-emerald-700">▌</span>}
            {meta && (
              <p className="mt-4 border-t border-slate-100 pt-2 text-xs text-slate-400">
                {meta.citations.length} verified citation
                {meta.citations.length === 1 ? "" : "s"} · {meta.model}
                {meta.invalid_citations.length > 0 &&
                  ` · ⚠ ${meta.invalid_citations.length} invalid citation(s) flagged`}
              </p>
            )}
          </div>
        )}
      </div>

      <aside className="lg:max-h-[75vh] lg:overflow-y-auto">
        <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-slate-500">
          Sources {sources.length > 0 && `(${sources.length})`}
        </h2>
        {sources.length === 0 ? (
          <p className="text-sm text-slate-400">
            Retrieved filing excerpts appear here after you ask a question.
          </p>
        ) : (
          <ol className="space-y-3">
            {sources.map((source, index) => (
              <li
                key={source.chunk_id}
                id={`source-${index + 1}`}
                className={`rounded-lg border bg-white p-3 text-sm transition-colors ${
                  activeSource === index + 1
                    ? "border-emerald-600 ring-1 ring-emerald-600"
                    : "border-slate-200"
                }`}
              >
                <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                  <span className="font-medium text-slate-700">
                    [{index + 1}] {source.form_type} · {source.filing_date}
                  </span>
                  <a
                    href={source.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-700 hover:underline"
                  >
                    SEC ↗
                  </a>
                </div>
                <div className="mb-1 text-xs text-slate-400">
                  {source.section ?? "Unlabeled section"}
                </div>
                <p className="line-clamp-6 whitespace-pre-line text-xs leading-relaxed text-slate-600">
                  {source.content}
                </p>
              </li>
            ))}
          </ol>
        )}
      </aside>
    </div>
  );
}
