"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { latestReportUrl, reportUrl } from "@/lib/api";

interface Citation {
  number: number;
  chunk_id: number;
  form_type: string;
  filing_date: string;
  section: string | null;
  source_url: string;
  content: string;
}

function linkCitations(markdown: string): string {
  return markdown.replace(/\[(\d{1,2})\]/g, "[[$1]](#report-source-$1)");
}

export default function ReportView({ ticker }: { ticker: string }) {
  const [content, setContent] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [stage, setStage] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [activeSource, setActiveSource] = useState<number | null>(null);

  // Show the stored report on first visit, if one exists
  useEffect(() => {
    fetch(latestReportUrl(ticker))
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (data) {
          setContent(data.content_md);
          setCitations(data.citations?.sources ?? []);
          setGeneratedAt(data.generated_at);
        }
      })
      .catch(() => undefined)
      .finally(() => setLoaded(true));
  }, [ticker]);

  async function generate() {
    setStreaming(true);
    setContent("");
    setCitations([]);
    setGeneratedAt(null);
    setError(null);
    setActiveSource(null);

    try {
      const response = await fetch(reportUrl(ticker), { method: "POST" });
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

          if (event === "status") setStage(data.stage);
          else if (event === "delta") setContent((prev) => prev + data.text);
          else if (event === "sources") setCitations(data.sources);
          else if (event === "done") {
            setStage(null);
            setGeneratedAt(new Date().toISOString());
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setStreaming(false);
      setStage(null);
    }
  }

  function onCitationClick(event: React.MouseEvent) {
    const anchor = (event.target as HTMLElement).closest("a");
    const href = anchor?.getAttribute("href");
    if (href?.startsWith("#report-source-")) {
      event.preventDefault();
      const index = Number(href.slice("#report-source-".length));
      setActiveSource(index);
      document
        .getElementById(`report-source-${index}`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  if (!loaded) {
    return <p className="text-sm text-slate-400">Loading…</p>;
  }

  return (
    <div>
      <div className="mb-6 flex items-center gap-4">
        <button
          onClick={generate}
          disabled={streaming}
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-40"
        >
          {streaming
            ? (stage ? `Generating: ${stage}…` : "Generating…")
            : content
              ? "Regenerate report"
              : "Generate report"}
        </button>
        {generatedAt && !streaming && (
          <span className="text-xs text-slate-400">
            Generated {new Date(generatedAt).toLocaleString()}
          </span>
        )}
      </div>

      {error && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {content && (
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <div
            onClick={onCitationClick}
            className="prose prose-sm prose-slate max-w-none rounded-lg border border-slate-200 bg-white p-6 [&_a[href^='#report-source-']]:rounded [&_a[href^='#report-source-']]:bg-emerald-100 [&_a[href^='#report-source-']]:px-1 [&_a[href^='#report-source-']]:font-medium [&_a[href^='#report-source-']]:text-emerald-800 [&_a[href^='#report-source-']]:no-underline [&_table]:text-xs"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {linkCitations(content)}
            </ReactMarkdown>
            {streaming && <span className="animate-pulse text-emerald-700">▌</span>}
          </div>

          <aside className="lg:max-h-[80vh] lg:overflow-y-auto">
            <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-slate-500">
              Sources {citations.length > 0 && `(${citations.length})`}
            </h2>
            {citations.length === 0 ? (
              <p className="text-sm text-slate-400">
                Citations appear when the report is complete.
              </p>
            ) : (
              <ol className="space-y-3">
                {citations.map((citation) => (
                  <li
                    key={citation.chunk_id}
                    id={`report-source-${citation.number}`}
                    className={`rounded-lg border bg-white p-3 text-sm transition-colors ${
                      activeSource === citation.number
                        ? "border-emerald-600 ring-1 ring-emerald-600"
                        : "border-slate-200"
                    }`}
                  >
                    <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                      <span className="font-medium text-slate-700">
                        [{citation.number}] {citation.form_type} ·{" "}
                        {citation.filing_date}
                      </span>
                      <a
                        href={citation.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-emerald-700 hover:underline"
                      >
                        SEC ↗
                      </a>
                    </div>
                    <div className="mb-1 text-xs text-slate-400">
                      {citation.section ?? "Unlabeled section"}
                    </div>
                    <p className="line-clamp-5 whitespace-pre-line text-xs leading-relaxed text-slate-600">
                      {citation.content}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </aside>
        </div>
      )}

      {!content && !streaming && (
        <p className="text-sm text-slate-500">
          No report yet. Generation takes about half a minute — the report is
          written section by section from the filings.
        </p>
      )}
    </div>
  );
}
