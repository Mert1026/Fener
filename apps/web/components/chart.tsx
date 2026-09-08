"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { RotateCcw, ZoomIn, ZoomOut } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import type { Model } from "@/lib/api";

export function ContextCostChart({ models }: { models: Model[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts | null>(null);
  const ranges = useRef([
    { dataZoomId: "price", start: 0, end: 100 },
    { dataZoomId: "context", start: 0, end: 100 },
  ]);
  const [zoom, setZoom] = useState("Full range");
  const { resolvedTheme } = useTheme();
  const router = useRouter();

  function changeZoom(factor: number | null) {
    const batch = ranges.current.map((range) => {
      if (factor === null) return { ...range, start: 0, end: 100 };
      const span = Math.min(
        100,
        Math.max(0.01, (range.end - range.start) * factor),
      );
      // Keep the crowded low-cost corner visible when zooming from the full view.
      const start =
        range.start === 0
          ? 0
          : Math.max(
              0,
              Math.min(100 - span, (range.start + range.end - span) / 2),
            );
      return { ...range, start, end: start + span };
    });
    instance.current?.dispatchAction({ type: "dataZoom", batch });
  }

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    instance.current = chart;
    const styles = getComputedStyle(ref.current);
    const foreground = styles.getPropertyValue("--muted").trim();
    const accent = styles.getPropertyValue("--accent").trim();
    const border = styles.getPropertyValue("--border").trim();
    const aqua = styles.getPropertyValue("--aqua").trim();
    const data = models
      .filter(
        (row) => row.input_price_from !== null && row.context_window !== null,
      )
      .map((row) => {
        const price = Number(row.input_price_from);
        return {
          name: row.name,
          free: price === 0,
          // The price axis is logarithmic; free models plot at the axis
          // floor and the aqua dot plus tooltip carry the truth.
          value: [price > 0 ? price : 0.001, row.context_window! / 1000],
          ...(price === 0
            ? { itemStyle: { color: aqua, borderColor: aqua } }
            : {}),
          id: row.id,
        };
      });
    chart.setOption({
      animation: false,
      aria: {
        enabled: true,
        decal: { show: true },
        label: {
          description:
            "Zoomable scatter chart comparing model context windows with lowest listed input prices. Each dot opens a model. This is not a quality benchmark.",
        },
      },
      grid: { left: 64, right: 28, top: 30, bottom: 46 },
      dataZoom: ranges.current.map((range, index) => ({
        id: range.dataZoomId,
        type: "inside",
        ...(index === 0 ? { xAxisIndex: 0 } : { yAxisIndex: 0 }),
        start: range.start,
        end: range.end,
        filterMode: "none",
        minSpan: 0.01,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: false,
      })),
      tooltip: {
        trigger: "item",
        renderMode: "richText",
        formatter: (p: unknown) => {
          const point = p as {
            data: { name: string; free?: boolean; value: number[] };
          };
          return `${point.data.name}\nInput: ${
            point.data.free ? "free" : `$${point.data.value[0]} / 1M`
          }\nContext: ${point.data.value[1]}K tokens`;
        },
      },
      xAxis: {
        type: "log",
        logBase: 10,
        min: 0.001,
        max: Math.max(1, ...data.map((point) => point.value[0] * 1.05)),
        name: "INPUT PRICE · USD / 1M · LOG",
        nameLocation: "middle",
        nameGap: 30,
        nameTextStyle: { fontSize: 9, color: foreground },
        axisLabel: {
          fontSize: 9,
          color: foreground,
          formatter: (v: number) => `$${v}`,
        },
        splitLine: {
          lineStyle: { color: border, type: "dashed" },
        },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      yAxis: {
        min: 0,
        max: Math.max(1, ...data.map((point) => point.value[1] * 1.05)),
        name: "CONTEXT · K TOKENS",
        nameTextStyle: { fontSize: 8, color: foreground },
        axisLabel: { fontSize: 9, color: foreground },
        splitLine: {
          lineStyle: { color: border, type: "dashed" },
        },
      },
      series: [
        {
          type: "scatter",
          symbolSize: 9,
          itemStyle: {
            color: accent,
            opacity: 0.8,
            borderColor: accent,
            borderWidth: 1,
            shadowBlur: 7,
            shadowColor: accent,
          },
          emphasis: { scale: 1.4, itemStyle: { opacity: 1, shadowBlur: 12 } },
          data,
        },
      ],
    });
    chart.on("datazoom", () => {
      const option = chart.getOption() as {
        dataZoom: { id: string; start: number; end: number }[];
      };
      ranges.current = ranges.current.map((range) => {
        const current = option.dataZoom.find(
          (item) => item.id === range.dataZoomId,
        );
        return current
          ? { ...range, start: current.start, end: current.end }
          : range;
      });
      const [price, context] = ranges.current.map(
        (range) => 100 / Math.max(0.01, range.end - range.start),
      );
      setZoom(
        price <= 1.001 && context <= 1.001
          ? "Full range"
          : `Price ${price.toFixed(1)}× · Context ${context.toFixed(1)}×`,
      );
    });
    chart.on("click", (params) => {
      if (params.componentType !== "series") return;
      const point = params.data as { id?: string };
      if (point?.id) router.push(`/models/${point.id}`);
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      instance.current = null;
      chart.dispose();
    };
  }, [models, resolvedTheme, router]);
  return (
    <div role="group" aria-label="Context and cost explorer">
      <div className="chart-controls">
        <button
          className="button"
          onClick={() => changeZoom(0.5)}
          aria-label="Zoom in on context and cost"
        >
          <ZoomIn size={13} /> Zoom in
        </button>
        <button
          className="button"
          onClick={() => changeZoom(2)}
          aria-label="Zoom out on context and cost"
        >
          <ZoomOut size={13} /> Zoom out
        </button>
        <button
          className="button"
          onClick={() => changeZoom(null)}
          aria-label="Reset context and cost zoom"
        >
          <RotateCcw size={12} /> Reset
        </button>
        <span className="small muted" role="status">
          {zoom}
        </span>
        <p className="chart-help" id="context-cost-help">
          Scroll or pinch to zoom · drag to pan · click a dot to open the model.
          Free models sit on the axis floor in aqua.
        </p>
      </div>
      <div
        ref={ref}
        className="chart context-cost-chart"
        role="img"
        aria-describedby="context-cost-help"
        aria-label="Zoomable scatter chart comparing model context windows with lowest listed input prices. Each dot opens a model. This is not a quality benchmark."
      />
    </div>
  );
}

const SERIES_PALETTE = {
  light: ["#002d72", "#0e7fb0", "#0f9d6a", "#a4681a", "#6b4fc9", "#40639c"],
  dark: ["#ffd60a", "#4cc9f0", "#3fd68f", "#ff9e64", "#b39cf0", "#5f8fe8"],
};

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
  const series = useMemo(() => {
    const groups = new Map<string, typeof rows>();
    for (const row of rows) {
      const key = `${row.provider} · ${row.metric} · ${row.source} · ${row.deployment_id.slice(0, 5)}`;
      groups.set(key, [...(groups.get(key) ?? []), row]);
    }
    return [...groups].slice(0, 12);
  }, [rows]);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const styles = getComputedStyle(ref.current);
    const foreground = styles.getPropertyValue("--muted").trim();
    const border = styles.getPropertyValue("--border").trim();
    chart.setOption({
      animation: false,
      aria: { enabled: true },
      color: SERIES_PALETTE[resolvedTheme === "light" ? "light" : "dark"],
      tooltip: { trigger: "axis", renderMode: "richText" },
      legend: { show: false },
      grid: { left: 60, right: 25, top: 25, bottom: 40 },
      xAxis: {
        type: "time",
        axisLabel: { color: foreground },
      },
      yAxis: {
        type: "value",
        name: "USD / 1M",
        splitLine: {
          lineStyle: {
            color: border,
          },
        },
        axisLabel: { color: foreground },
      },
      series: series.map(([name, values]) => ({
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
  }, [series, resolvedTheme]);
  const palette = SERIES_PALETTE[resolvedTheme === "light" ? "light" : "dark"];
  return (
    <>
      <div
        ref={ref}
        className="chart"
        role="img"
        aria-label="Observed historical prices, separated by deployment, metric, and source. Single observations appear as points."
      />
      {series.length > 1 && (
        <div className="chart-legend">
          {series.map(([name], index) => (
            <span className="chart-legend-item" key={name} title={name}>
              <span
                className="chart-legend-dot"
                style={{ background: palette[index % palette.length] }}
              />
              {name.split(" · ").slice(0, 3).join(" · ").replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}
    </>
  );
}
