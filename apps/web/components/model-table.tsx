"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import {
  ArrowDownUp,
  Braces,
  BrainCircuit,
  Eye,
  SlidersHorizontal,
  Wrench,
} from "lucide-react";
import type { Model } from "@/lib/api";
import { money, tokens } from "@/lib/format";
import { useCompare } from "@/lib/compare-store";
import { useColumns } from "@/lib/column-store";
import { Badge, EvidenceValue } from "./ui";

const helper = createColumnHelper<Model>();
export function ModelTable({
  models,
  compact = false,
}: {
  models: Model[];
  compact?: boolean;
}) {
  const { selected, toggle } = useCompare();
  const [sorting, setSorting] = useState<SortingState>([]);
  const { visibility, setVisibility } = useColumns();
  const columns = useMemo(
    () => [
      helper.display({
        id: "select",
        header: "",
        cell: ({ row }) => (
          <input
            type="checkbox"
            aria-label={`Compare ${row.original.name}`}
            checked={selected.some((item) => item.id === row.original.id)}
            onChange={() =>
              toggle({ id: row.original.id, name: row.original.name })
            }
            disabled={
              selected.length >= 6 &&
              !selected.some((item) => item.id === row.original.id)
            }
          />
        ),
      }),
      helper.accessor("name", {
        header: "Model",
        cell: ({ row }) => (
          <div className="model-identity">
            <span className="model-avatar">
              {(row.original.publisher ?? row.original.name)
                .slice(0, 2)
                .toUpperCase()}
            </span>
            <Link href={`/models/${row.original.id}`}>
              <strong>{row.original.name}</strong>
              <small>
                {row.original.publisher ?? "Unresolved publisher"}{" "}
                <span className="muted">/</span>{" "}
                {row.original.family ?? "Unclassified"}
              </small>
            </Link>
          </div>
        ),
      }),
      helper.accessor("publisher", {
        header: "Publisher",
        cell: (info) => info.getValue() ?? "Unknown",
      }),
      helper.accessor("context_window", {
        header: "Context",
        cell: ({ row }) => (
          <EvidenceValue fact={row.original.facts.context_window}>
            <span className="mono">{tokens(row.original.context_window)}</span>
          </EvidenceValue>
        ),
      }),
      helper.accessor("input_price_from", {
        header: "Input from",
        cell: (info) => (
          <EvidenceValue
            fact={info.row.original.input_price_evidence ?? undefined}
          >
            <span className="mono">{money(info.getValue())}</span>
          </EvidenceValue>
        ),
        sortingFn: (a, b) =>
          Number(a.original.input_price_from ?? Infinity) -
          Number(b.original.input_price_from ?? Infinity),
      }),
      helper.accessor("output_price_from", {
        header: "Output from",
        cell: (info) => (
          <EvidenceValue
            fact={info.row.original.output_price_evidence ?? undefined}
          >
            <span className="mono">{money(info.getValue())}</span>
          </EvidenceValue>
        ),
        sortingFn: (a, b) =>
          Number(a.original.output_price_from ?? Infinity) -
          Number(b.original.output_price_from ?? Infinity),
      }),
      helper.accessor("deployment_count", {
        header: "Listings",
        cell: (info) => <span className="mono muted">{info.getValue()}</span>,
      }),
      helper.accessor("capabilities", {
        header: "Capabilities",
        enableSorting: false,
        cell: (info) => (
          <div className="capability-icons">
            {[
              { key: "reasoning", name: "Reasoning", icon: BrainCircuit },
              { key: "tool_calling", name: "Tool calling", icon: Wrench },
              { key: "image_input", name: "Image input", icon: Eye },
              {
                key: "structured_output",
                name: "Structured output",
                icon: Braces,
              },
            ]
              .filter((item) => info.getValue().includes(item.key))
              .map((item) => (
                <span key={item.key} title={item.name}>
                  <item.icon size={12} />
                  <span className="sr-only">{item.name}</span>
                </span>
              ))}
          </div>
        ),
      }),
      helper.accessor("open_weights", {
        header: "Weights",
        cell: (info) =>
          info.getValue() == null ? (
            <span className="muted">Unknown</span>
          ) : (
            <Badge tone={info.getValue() ? "good" : "neutral"}>
              {info.getValue() ? "Open" : "Closed"}
            </Badge>
          ),
      }),
    ],
    [selected, toggle],
  );
  // TanStack Table is intentionally a stateful table API; its row model is consumed directly.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: models,
    columns,
    state: { sorting, columnVisibility: visibility },
    onSortingChange: setSorting,
    onColumnVisibilityChange: setVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  return (
    <>
      {!compact && (
        <div className="section-row">
          <p>
            {models.length} models on this page <span className="muted">·</span>{" "}
            Click a value to inspect its evidence
          </p>
          <details className="columns-menu">
            <summary className="button">
              <SlidersHorizontal size={12} /> Columns
            </summary>
            <div className="columns-options">
              {table
                .getAllLeafColumns()
                .filter(
                  (column) => column.id !== "select" && column.id !== "name",
                )
                .map((column) => (
                  <label key={column.id}>
                    <input
                      type="checkbox"
                      checked={column.getIsVisible()}
                      onChange={column.getToggleVisibilityHandler()}
                    />
                    {String(column.columnDef.header)}
                  </label>
                ))}
            </div>
          </details>
        </div>
      )}
      <div className="table-wrap">
        <table className="responsive-table">
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th
                    className={
                      [
                        "output_price_from",
                        "capabilities",
                        "open_weights",
                        "deployment_count",
                        "publisher",
                      ].includes(header.column.id)
                        ? "hide-mobile"
                        : ""
                    }
                    key={header.id}
                  >
                    {header.isPlaceholder ? null : header.column.getCanSort() ? (
                      <button onClick={header.column.getToggleSortingHandler()}>
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                        <ArrowDownUp size={9} />
                      </button>
                    ) : (
                      flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td
                    className={
                      [
                        "output_price_from",
                        "capabilities",
                        "open_weights",
                        "deployment_count",
                        "publisher",
                      ].includes(cell.column.id)
                        ? "hide-mobile"
                        : ""
                    }
                    key={cell.id}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
