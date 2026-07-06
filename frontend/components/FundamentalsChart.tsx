"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Fundamental } from "@/lib/api";

export default function FundamentalsChart({
  fundamentals,
}: {
  fundamentals: Fundamental[];
}) {
  const byYear = new Map<number, { year: number; revenue?: number; netIncome?: number }>();
  for (const fact of fundamentals) {
    if (fact.metric !== "revenue" && fact.metric !== "net_income") continue;
    const entry = byYear.get(fact.fiscal_year) ?? { year: fact.fiscal_year };
    if (fact.metric === "revenue") entry.revenue = fact.value / 1e9;
    if (fact.metric === "net_income") entry.netIncome = fact.value / 1e9;
    byYear.set(fact.fiscal_year, entry);
  }
  const data = [...byYear.values()]
    .sort((a, b) => a.year - b.year)
    .slice(-8);

  if (data.length === 0) {
    return <p className="text-sm text-slate-400">No fundamentals available.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="year" tick={{ fontSize: 12, fill: "#64748b" }} />
        <YAxis
          tick={{ fontSize: 12, fill: "#64748b" }}
          tickFormatter={(value: number) => `$${value.toFixed(0)}B`}
        />
        <Tooltip
          formatter={(value) => [`$${Number(value).toFixed(1)}B`]}
          labelFormatter={(year) => `FY${year}`}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="revenue" name="Revenue" fill="#047857" radius={[3, 3, 0, 0]} />
        <Bar dataKey="netIncome" name="Net income" fill="#93c5fd" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
