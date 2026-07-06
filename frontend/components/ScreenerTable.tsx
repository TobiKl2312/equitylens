"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  ScreenerRow,
  formatBillions,
  formatPercent,
  formatPrice,
} from "@/lib/api";

type SortKey = "ticker" | "last_close" | "revenue" | "net_income" | "net_margin";

const COLUMNS: { key: SortKey; label: string; align: "left" | "right" }[] = [
  { key: "ticker", label: "Company", align: "left" },
  { key: "last_close", label: "Last close", align: "right" },
  { key: "revenue", label: "Revenue (FY)", align: "right" },
  { key: "net_income", label: "Net income (FY)", align: "right" },
  { key: "net_margin", label: "Net margin", align: "right" },
];

export default function ScreenerTable({ rows }: { rows: ScreenerRow[] }) {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("ticker");
  const [descending, setDescending] = useState(false);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const filtered = rows.filter(
      (row) =>
        !needle ||
        row.ticker.toLowerCase().includes(needle) ||
        row.name.toLowerCase().includes(needle),
    );
    return filtered.sort((a, b) => {
      if (sortKey === "ticker") {
        return descending
          ? b.ticker.localeCompare(a.ticker)
          : a.ticker.localeCompare(b.ticker);
      }
      const av = a[sortKey] ?? -Infinity;
      const bv = b[sortKey] ?? -Infinity;
      return descending ? bv - av : av - bv;
    });
  }, [rows, search, sortKey, descending]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setDescending(!descending);
    } else {
      setSortKey(key);
      setDescending(key !== "ticker");
    }
  }

  return (
    <div>
      <input
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search ticker or name…"
        className="mb-4 w-full max-w-xs rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-600"
      />
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-100 text-xs uppercase tracking-wide text-slate-500">
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  onClick={() => toggleSort(column.key)}
                  className={`cursor-pointer select-none px-4 py-3 font-medium hover:text-slate-900 ${
                    column.align === "right" ? "text-right" : "text-left"
                  }`}
                >
                  {column.label}
                  {sortKey === column.key ? (descending ? " ↓" : " ↑") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr
                key={row.ticker}
                className="border-b border-slate-100 last:border-0 hover:bg-emerald-50/40"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/company/${row.ticker}`}
                    className="font-medium text-emerald-700 hover:underline"
                  >
                    {row.ticker}
                  </Link>
                  <span className="ml-2 text-slate-500">{row.name}</span>
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatPrice(row.last_close)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatBillions(row.revenue)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatBillions(row.net_income)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums">
                  {formatPercent(row.net_margin)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
