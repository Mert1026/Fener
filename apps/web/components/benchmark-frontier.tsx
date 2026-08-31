"use client";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { useTheme } from "next-themes";
import Link from "next/link";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { Badge, Empty, ErrorState, Loading } from "./ui";
type Metric = {
  metric: string;
  name: string;
  version: string;
  evaluator: string;
};
type Point = {
  deployment_id: string;
  model_id: string;
  model_name: string;
  provider: string;
  cost: string;
  quality: string;
  pareto: boolean;
};
function Plot({ points }: { points: Point[] }) {
  const element = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();
  useEffect(() => {
    if (!element.current) return;
    const chart = echarts.init(element.current);
    const styles = getComputedStyle(element.current);
    const ink = styles.getPropertyValue("--muted").trim();
    const accent = styles.getPropertyValue("--accent").trim();
    chart.setOption({
      animation: false,
      aria: { enabled: true },
      grid: { left: 60, right: 25, top: 35, bottom: 50 },
      tooltip: {
        renderMode: "richText",
        formatter: (value: unknown) => {
          const row = (value as { data: { name: string; value: number[] } })
            .data;
          return `${row.name}\n$${row.value[0]} / workload\nQuality ${(row.value[1] * 100).toFixed(1)}%`;
        },
      },
      xAxis: {
        name: "WORKLOAD COST · USD",
        nameLocation: "middle",
        nameGap: 30,
        axisLabel: { color: ink },
      },
      yAxis: {
        name: "NORMALIZED QUALITY",
        min: 0,
        max: 1,
        axisLabel: { color: ink },
      },
      series: [false, true].map((frontier) => ({
        type: "scatter",
        name: frontier ? "Pareto frontier" : "Dominated",
        symbolSize: frontier ? 12 : 7,
        itemStyle: { color: frontier ? accent : ink },
        data: points
          .filter((p) => p.pareto === frontier)
          .map((p) => ({
            name: `${p.model_name} · ${p.provider}`,
            value: [Number(p.cost), Number(p.quality)],
          })),
      })),
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [points, resolvedTheme]);
  return (
    <div
      className="chart"
      ref={element}
      role="img"
      aria-label="Price quality scatter with Pareto efficient deployments highlighted; accessible data follows in the table."
    />
  );
}
export function BenchmarkFrontier() {
  const metrics = useQuery({
    queryKey: ["normalized-benchmarks"],
    queryFn: () => api<Metric[]>("analytics/benchmarks"),
  });
  const [chosen, setChosen] = useState("");
  const options = [
    ...new Map((metrics.data ?? []).map((m) => [m.metric, m])).values(),
  ];
  const frontier = useMutation({
    mutationFn: () =>
      api<{ points: Point[]; reason: string | null }>("analytics/frontier", {
        method: "POST",
        body: JSON.stringify({
          weights: { [chosen || options[0]?.metric]: "1" },
          workload: { requests: 10000, input_tokens: 2000, output_tokens: 500 },
        }),
      }),
  });
  return (
    <section className="panel" style={{ marginTop: 28 }}>
      <div className="panel-header">
        <div>
          <h2>Quality for the money</h2>
          <p>
            Exact benchmark version and evaluator. Larger highlighted points
            cannot be beaten on both cost and measured quality.
          </p>
        </div>
        <Badge>Strict dominance</Badge>
      </div>
      {metrics.isPending ? (
        <Loading />
      ) : metrics.error ? (
        <ErrorState error={metrics.error} retry={metrics.refetch} />
      ) : !options.length ? (
        <Empty title="Comparable evidence required">
          No verified version, evaluator and scale are available together yet.
          The price / quality scatter and Pareto frontier stay empty until those
          requirements are met.
        </Empty>
      ) : (
        <div className="settings-panel">
          <label htmlFor="frontier-metric">Benchmark / evaluator</label>
          <select
            id="frontier-metric"
            value={chosen || options[0].metric}
            onChange={(e) => {
              setChosen(e.target.value);
              frontier.reset();
            }}
          >
            {options.map((m) => (
              <option key={m.metric} value={m.metric}>
                {m.name} · {m.version} · {m.evaluator}
              </option>
            ))}
          </select>
          <p>
            10,000 requests × 2,000 input + 500 output tokens. Unknown prices,
            stale serving facts and unbound routing quotes are excluded.
          </p>
          <button
            className="button primary"
            disabled={frontier.isPending}
            onClick={() => frontier.mutate()}
          >
            Calculate frontier
          </button>
          {frontier.error && (
            <ErrorState error={frontier.error} retry={frontier.reset} />
          )}
          {frontier.data?.reason && <p role="status">{frontier.data.reason}</p>}
          {!!frontier.data?.points.length && (
            <>
              <Plot points={frontier.data.points} />
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Model / provider</th>
                      <th>Workload cost</th>
                      <th>Normalized quality</th>
                      <th>Frontier</th>
                    </tr>
                  </thead>
                  <tbody>
                    {frontier.data.points.map((p) => (
                      <tr key={p.deployment_id}>
                        <td>
                          <Link href={`/models/${p.model_id}`}>
                            {p.model_name}
                          </Link>{" "}
                          · {p.provider}
                        </td>
                        <td>{money(p.cost)}</td>
                        <td>{(Number(p.quality) * 100).toFixed(1)}%</td>
                        <td>
                          <Badge tone={p.pareto ? "good" : "neutral"}>
                            {p.pareto ? "Efficient" : "Dominated"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
