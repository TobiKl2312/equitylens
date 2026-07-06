import Link from "next/link";
import { notFound } from "next/navigation";
import { api, formatBillions, formatPrice } from "@/lib/api";
import PriceChart from "@/components/PriceChart";
import FundamentalsChart from "@/components/FundamentalsChart";

export const dynamic = "force-dynamic";

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  let company;
  try {
    company = await api.company(ticker);
  } catch {
    notFound();
  }

  const [prices, fundamentals, filings] = await Promise.all([
    api.prices(ticker),
    api.fundamentals(ticker),
    api.filings(ticker),
  ]);

  const lastPrice = prices.at(-1);
  const annual = fundamentals.filter((f) => f.fiscal_period === "FY");
  const latestRevenue = annual
    .filter((f) => f.metric === "revenue")
    .sort((a, b) => b.fiscal_year - a.fiscal_year)[0];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            {company.name}
            <span className="ml-3 text-lg font-normal text-slate-400">
              {company.ticker}
            </span>
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {lastPrice
              ? `${formatPrice(lastPrice.adj_close ?? lastPrice.close)} · ${lastPrice.date}`
              : "No price data"}
            {latestRevenue &&
              ` · Revenue FY${latestRevenue.fiscal_year}: ${formatBillions(latestRevenue.value)}`}
          </p>
        </div>
        <Link
          href={`/company/${company.ticker}/chat`}
          className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
        >
          Ask the filings →
        </Link>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">
          Price (2y, adjusted close)
        </h2>
        <PriceChart
          data={prices
            .filter((p) => (p.adj_close ?? p.close) !== null)
            .map((p) => ({ time: p.date, value: (p.adj_close ?? p.close)! }))}
        />
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">
          Annual fundamentals (SEC XBRL)
        </h2>
        <FundamentalsChart fundamentals={annual} />
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">
          SEC filings
        </h2>
        <ul className="divide-y divide-slate-100 text-sm">
          {filings.slice(0, 10).map((filing) => (
            <li key={filing.id} className="flex items-center justify-between py-2">
              <span>
                <span className="font-medium">{filing.form_type}</span>
                <span className="ml-2 text-slate-500">
                  filed {filing.filing_date}
                  {filing.period_end && ` · period ${filing.period_end}`}
                </span>
                {filing.ingest_status === "embedded" && (
                  <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 text-xs text-emerald-800">
                    searchable
                  </span>
                )}
              </span>
              <a
                href={filing.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-emerald-700 hover:underline"
              >
                SEC ↗
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
