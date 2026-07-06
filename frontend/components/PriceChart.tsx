"use client";

import { useEffect, useRef } from "react";
import { AreaSeries, ColorType, createChart } from "lightweight-charts";

export default function PriceChart({
  data,
}: {
  data: { time: string; value: number }[];
}) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current || data.length === 0) return;

    const chart = createChart(container.current, {
      height: 320,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#64748b",
      },
      grid: {
        vertLines: { color: "#f1f5f9" },
        horzLines: { color: "#f1f5f9" },
      },
      rightPriceScale: { borderColor: "#e2e8f0" },
      timeScale: { borderColor: "#e2e8f0" },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#047857",
      topColor: "rgba(4, 120, 87, 0.25)",
      bottomColor: "rgba(4, 120, 87, 0.02)",
      lineWidth: 2,
    });
    series.setData(data);
    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      if (container.current) {
        chart.applyOptions({ width: container.current.clientWidth });
      }
    });
    observer.observe(container.current);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [data]);

  if (data.length === 0) {
    return <p className="text-sm text-slate-400">No price data available.</p>;
  }
  return <div ref={container} className="w-full" />;
}
