import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import Chat from "@/components/Chat";

export const dynamic = "force-dynamic";

export default async function ChatPage({
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
          Ask the filings — {company.name}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Answers come only from {company.ticker}&apos;s 10-K/10-Q filings.
          Every claim carries a citation you can verify on the right.
        </p>
      </div>
      <Chat ticker={company.ticker} />
    </div>
  );
}
