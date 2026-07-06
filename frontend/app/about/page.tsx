export default function AboutPage() {
  return (
    <div className="prose prose-slate max-w-2xl">
      <h1>About EquityLens</h1>
      <p>
        EquityLens is an AI investment research platform built as an
        educational portfolio project. It aggregates SEC filings, XBRL
        fundamentals, and market data for 35 US large caps and answers
        questions about them with a citation-grounded RAG pipeline — every
        claim is traceable to the exact passage in a 10-K or 10-Q.
      </p>
      <h2>How it works</h2>
      <ul>
        <li>
          <strong>Data:</strong> SEC EDGAR (filings + XBRL fundamentals) and
          daily EOD prices, ingested idempotently into PostgreSQL.
        </li>
        <li>
          <strong>RAG:</strong> filings are split along their item structure,
          chunked, and embedded with finance-tuned embeddings
          (voyage-finance-2) into pgvector. Retrieval combines vector
          similarity with SQL metadata filters.
        </li>
        <li>
          <strong>Answers:</strong> Claude answers strictly from retrieved
          excerpts; citations are validated server-side against the sources
          actually provided.
        </li>
      </ul>
      <p>
        Source code, architecture decision records, and the retrieval
        evaluation are on{" "}
        <a
          href="https://github.com/TobiKl2312/equitylens"
          target="_blank"
          rel="noreferrer"
        >
          GitHub
        </a>
        .
      </p>
      <p>
        <em>Nothing on this site is investment advice.</em>
      </p>
    </div>
  );
}
