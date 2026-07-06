const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface ScreenerRow {
  ticker: string;
  name: string;
  last_close: number | null;
  last_close_date: string | null;
  revenue: number | null;
  net_income: number | null;
  net_margin: number | null;
  fiscal_year: number | null;
}

export interface Company {
  id: number;
  ticker: string;
  name: string;
  cik: number | null;
  sector: string | null;
  industry: string | null;
}

export interface Price {
  date: string;
  close: number | null;
  adj_close: number | null;
  volume: number | null;
}

export interface Fundamental {
  metric: string;
  value: number;
  unit: string;
  fiscal_year: number;
  fiscal_period: string;
  period_end: string;
  form: string;
}

export interface Filing {
  id: number;
  form_type: string;
  filing_date: string;
  period_end: string | null;
  accession_no: string;
  source_url: string;
  ingest_status: string;
}

export interface Source {
  chunk_id: number;
  filing_id: number;
  section: string | null;
  content: string;
  form_type: string;
  filing_date: string;
  source_url: string;
  distance: number;
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API ${response.status} for ${path}`);
  }
  return response.json();
}

export const api = {
  screener: () => get<ScreenerRow[]>("/screener"),
  company: (ticker: string) => get<Company>(`/companies/${ticker}`),
  prices: (ticker: string) => get<Price[]>(`/companies/${ticker}/prices`),
  fundamentals: (ticker: string) =>
    get<Fundamental[]>(`/companies/${ticker}/fundamentals`),
  filings: (ticker: string) => get<Filing[]>(`/companies/${ticker}/filings`),
};

export function chatUrl(ticker: string): string {
  return `${API_URL}/companies/${ticker}/chat`;
}

export function reportUrl(ticker: string): string {
  return `${API_URL}/companies/${ticker}/report`;
}

export function latestReportUrl(ticker: string): string {
  return `${API_URL}/companies/${ticker}/report`;
}

export function formatBillions(value: number | null): string {
  if (value === null) return "–";
  return `$${(value / 1e9).toFixed(1)}B`;
}

export function formatPercent(value: number | null): string {
  if (value === null) return "–";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatPrice(value: number | null): string {
  if (value === null) return "–";
  return `$${value.toFixed(2)}`;
}
