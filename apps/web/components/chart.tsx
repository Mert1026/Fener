"use client";
import { useEffect, useRef, useState } from "react";
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
    const surface = styles.getPropertyValue("--surface").trim();
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
      aria: {
        enabled: true,
        decal: { show: true },
        label: {
          description:
            "Zoomable scatter chart comparing model context windows with lowest listed input prices. Each dot opens a model. This is not a quality benchmark.",
        },
      },
      grid: { left: 57, right: 53, top: 28, bottom: 85 },
      dataZoom: [
        ...ranges.current.map((range, index) => ({
          id: range.dataZoomId,
          type: "slider",
          ...(index === 0
            ? { xAxisIndex: 0, bottom: 15, height: 18, left: 57, right: 53 }
            : { yAxisIndex: 0, right: 13, width: 16, top: 28, bottom: 85 }),
          start: range.start,
          end: range.end,
          filterMode: "none",
          minSpan: 0.01,
          showDetail: false,
          showDataShadow: false,
          borderColor: border,
          backgroundColor: surface,
          fillerColor: resolvedTheme === "light" ? "#002d7226" : "#ffed0026",
          handleStyle: { color: accent, borderColor: accent },
          moveHandleStyle: { color: accent },
          brushSelect: false,
        })),
        ...["xAxisIndex", "yAxisIndex"].map((axis) => ({
          type: "inside",
          [axis]: 0,
          filterMode: "none",
          minSpan: 0.01,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          moveOnMouseWheel: false,
        })),
      ],
      tooltip: {
        trigger: "item",
        renderMode: "richText",
        formatter: (p: unknown) => {
          const point = p as { data: { name: string; value: number[] } };
          return `${point.data.name}\nInput: $${point.data.value[0]} / 1M\nContext: ${point.data.value[1]}K`;
        },
      },
      xAxis: {
        min: 0,
        max: Math.max(1, ...data.map((point) => point.value[0] * 1.05)),
        name: "INPUT PRICE · USD / 1M",
        nameLocation: "middle",
        nameGap: 31,
        nameTextStyle: { fontSize: 9, color: foreground },
        axisLabel: { fontSize: 9, color: foreground },
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
          symbolSize: 8,
          itemStyle: {
            color: accent,
            opacity: 0.75,
            borderColor: accent,
            borderWidth: 1,
          },
          emphasis: { scale: 1.5, itemStyle: { opacity: 1 } },
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
          Scroll or pinch to zoom, drag to pan, or adjust either axis with its
          slider. Identical values still overlap.
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
    const styles = getComputedStyle(ref.current);
    const foreground = styles.getPropertyValue("--muted").trim();
    const border = styles.getPropertyValue("--border").trim();
    for (const row of rows) {
      const key = `${row.provider} · ${row.metric} · ${row.source} · ${row.deployment_id.slice(0, 5)}`;
      groups.set(key, [...(groups.get(key) ?? []), row]);
    }
    chart.setOption({
      animation: false,
      aria: { enabled: true },
      color:
        resolvedTheme === "light"
          ? ["#002d72", "#887500", "#2869b4", "#547899", "#796831", "#425481"]
          : ["#ffed00", "#70a6ec", "#f4cf72", "#a5bfdf", "#c7c35d", "#4e89d9"],
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
