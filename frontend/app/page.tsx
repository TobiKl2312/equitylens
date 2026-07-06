import { api } from "@/lib/api";
import ScreenerTable from "@/components/ScreenerTable";

export const dynamic = "force-dynamic";

export default async function ScreenerPage() {
  const rows = await api.screener();
  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold">Screener</h1>
      <p className="mb-6 text-sm text-slate-500">
        {rows.length} US large caps — latest close and most recent fiscal-year
        fundamentals from SEC XBRL data.
      </p>
      <ScreenerTable rows={rows} />
    </div>
  );
}
