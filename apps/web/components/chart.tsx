"use client";
import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import type { Model } from "@/lib/api";

export function ContextCostChart({ models }: { models: Model[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();
  const router = useRouter();
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const light = resolvedTheme === "light";
    const foreground = light ? "#667085" : "#8993a4";
    const data = models
      .filter(
        (row) => row.input_price_from !== null && row.context_window !== null,
      )
      .map((row) => ({
        name: row.name,
        value: [Number(row.input_price_from), row.context_window! / 1000],
        id: row.id,
      }));
    chart.setOption({
      animation: false,
      aria: { enabled: true, decal: { show: true } },
      grid: { left: 57, right: 23, top: 24, bottom: 48 },
      tooltip: {
        trigger: "item",
        renderMode: "richText",
        formatter: (p: unknown) => {
          const point = p as { data: { name: string; value: number[] } };
          return `${point.data.name}\nInput: $${point.data.value[0]} / 1M\nContext: ${point.data.value[1]}K`;
        },
      },
      xAxis: {
        name: "INPUT PRICE · USD / 1M",
        nameLocation: "middle",
        nameGap: 31,
        nameTextStyle: { fontSize: 9, color: foreground },
        axisLabel: { fontSize: 9, color: foreground },
        splitLine: {
          lineStyle: { color: light ? "#e8ebf0" : "#272c35", type: "dashed" },
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        name: "CONTEXT · K TOKENS",
        nameTextStyle: { fontSize: 8, color: foreground },
        axisLabel: { fontSize: 9, color: foreground },
        splitLine: {
          lineStyle: { color: light ? "#e8ebf0" : "#272c35", type: "dashed" },
        },
      },
      series: [
        {
          type: "scatter",
          symbolSize: 8,
          itemStyle: {
            color: "#93a9fa",
            opacity: 0.75,
            borderColor: light ? "#455dd2" : "#b9c7ff",
            borderWidth: 1,
          },
          emphasis: { itemStyle: { color: "#9fdbca" } },
          data,
        },
      ],
    });
    chart.on("click", (params) => {
      const point = params.data as { id?: string };
      if (point.id) router.push(`/models/${point.id}`);
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [models, resolvedTheme, router]);
  return (
    <div
      ref={ref}
      className="chart"
      role="img"
      aria-label="Scatter chart comparing model context windows with lowest listed input prices. Each dot opens a model. This is not a quality benchmark."
    />
  );
}

export function PriceHistoryChart({
  rows,
}: {
  rows: {
    observed_at: string;
    amount: string;
    provider: string;
    metric: string;
    deployment_id: string;
    source: string;
  }[];
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const groups = new Map<string, typeof rows>();
    for (const row of rows) {
      const key = `${row.provider} · ${row.metric} · ${row.source} · ${row.deployment_id.slice(0, 5)}`;
      groups.set(key, [...(groups.get(key) ?? []), row]);
    }
    chart.setOption({
      animation: false,
      aria: { enabled: true },
      tooltip: { trigger: "axis", renderMode: "richText" },
      legend: { show: false },
      grid: { left: 60, right: 25, top: 25, bottom: 40 },
      xAxis: {
        type: "time",
        axisLabel: { color: resolvedTheme === "light" ? "#667085" : "#8993a4" },
      },
      yAxis: {
        type: "value",
        name: "USD / 1M",
        splitLine: {
          lineStyle: {
            color: resolvedTheme === "light" ? "#e8ebf0" : "#272c35",
          },
        },
        axisLabel: { color: "#8993a4" },
      },
      series: [...groups].slice(0, 12).map(([name, values]) => ({
        name,
        type: "line",
        step: "end",
        symbolSize: 7,
        data: values
          .sort((a, b) => a.observed_at.localeCompare(b.observed_at))
          .map((row) => [row.observed_at, Number(row.amount)]),
      })),
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [rows, resolvedTheme]);
  return (
    <div
      ref={ref}
      className="chart"
      role="img"
      aria-label="Observed historical prices, separated by deployment, metric, and source. Single observations appear as points."
    />
  );
}
