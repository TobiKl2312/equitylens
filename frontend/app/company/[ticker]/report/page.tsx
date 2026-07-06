import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import ReportView from "@/components/ReportView";

export const dynamic = "force-dynamic";

export default async function ReportPage({
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

  return (
    <div>
      <div className="mb-6">
        <Link
          href={`/company/${company.ticker}`}
          className="text-sm text-emerald-700 hover:underline"
        >
          ← {company.ticker} dashboard
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">
          Research report — {company.name}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Generated section by section from {company.ticker}&apos;s filings.
          Figures come from SEC XBRL data; claims carry verifiable citations.
        </p>
      </div>
      <ReportView ticker={company.ticker} />
    </div>
  );
}
