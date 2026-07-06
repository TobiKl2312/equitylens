# EquityLens frontend

Next.js 16 (App Router, TypeScript, Tailwind v4). Pages:

- `/` — screener: sortable/searchable table of the universe with latest
  close and fiscal-year fundamentals (single `/screener` API call)
- `/company/[ticker]` — dashboard: 2y price chart (lightweight-charts),
  annual revenue/net-income chart (recharts), SEC filings list
- `/company/[ticker]/chat` — RAG chat: SSE streaming answer with
  clickable `[n]` citation chips that highlight the source excerpt in the
  side panel; invalid citations flagged from the server's `done` event
- `/about`

## Development

The backend API must be running on `localhost:8000` (see root README).

```bash
npm install
npm run dev     # http://localhost:3000
npm run build   # type-check + production build
```

Set `NEXT_PUBLIC_API_URL` to point at a non-local API.
