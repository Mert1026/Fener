"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import {
  Activity,
  ArrowLeftRight,
  ArrowUpRight,
  Boxes,
  Check,
  ChevronRight,
  Compass,
  ScanSearch,
  House,
  Layers3,
  Menu,
  Moon,
  Radio,
  Search,
  Settings2,
  ShieldCheck,
  Sun,
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api, type ModelPage } from "@/lib/api";
import { useCompare } from "@/lib/compare-store";

const navigation = [
  {
    label: "Market",
    items: [
      { href: "/", name: "Overview", icon: House },
      { href: "/models", name: "Models", icon: Boxes },
      { href: "/providers", name: "Providers", icon: Layers3 },
      { href: "/compare", name: "Compare", icon: ArrowLeftRight },
      { href: "/benchmarks", name: "Benchmarks", icon: Activity },
      { href: "/market", name: "Market feed", icon: Radio },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/find", name: "Find a model", icon: Compass },
      { href: "/research", name: "AI research", icon: ScanSearch },
    ],
  },
  {
    label: "Workspace",
    items: [
      { href: "/data-health", name: "Data health", icon: ShieldCheck },
      { href: "/settings", name: "Settings", icon: Settings2 },
    ],
  },
];

function SearchPalette({ close }: { close: () => void }) {
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    return () => {
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, []);
  const [q, setQ] = useState("");
  const router = useRouter();
  const result = useQuery({
    queryKey: ["search", q],
    queryFn: () => api<ModelPage>(`models?q=${encodeURIComponent(q)}&limit=8`),
    enabled: q.length > 1,
  });
  return (
    <div className="modal-backdrop" onClick={close}>
      <section
        ref={dialog}
        className="search-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Search models"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key !== "Tab") return;
          const items = dialog.current?.querySelectorAll<HTMLElement>(
            "input,button,a[href]",
          );
          if (!items?.length) return;
          const first = items[0],
            last = items[items.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }}
      >
        <div className="search-input">
          <Search size={18} />
          <input
            autoFocus
            aria-label="Search model catalog"
            placeholder="Search models, publishers, aliases…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") close();
              if (e.key === "Enter" && result.data?.items[0]) {
                router.push(`/models/${result.data.items[0].id}`);
                close();
              }
            }}
          />
          <button
            className="icon-button"
            aria-label="Close search"
            onClick={close}
          >
            <X size={18} />
          </button>
        </div>
        <div className="search-results">
          {result.data?.items.map((model) => (
            <Link key={model.id} href={`/models/${model.id}`} onClick={close}>
              <Boxes size={16} />
              <span>
                {model.name}
                <small>{model.publisher ?? "Publisher unknown"}</small>
              </span>
              <ChevronRight size={15} />
            </Link>
          ))}
          {q.length < 2 ? (
            <p>Type at least two characters to search the catalog.</p>
          ) : (
            !result.data?.items.length && (
              <p>{result.isFetching ? "Searching…" : "No matching models."}</p>
            )
          )}
        </div>
      </section>
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [search, setSearch] = useState(false);
  const [mobile, setMobile] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();
  const { selected, clear } = useCompare();
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setSearch((value) => !value);
      }
      if (e.key === "Escape") {
        setSearch(false);
        setMobile(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  const current = navigation
    .flatMap((group) => group.items)
    .find((item) =>
      item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
    );
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${mobile ? "is-open" : ""}`}>
        <Link className="brand" href="/">
          <span className="brand-mark">
            <span />
            <span />
            <span />
          </span>
          <span>
            fener<span className="brand-dot">.</span>
          </span>
          <span className="workspace-tag">INTELLIGENCE</span>
        </Link>
        <button className="sidebar-search" onClick={() => setSearch(true)}>
          <Search size={15} />
          <span>Search anything</span>
          <kbd>⌘ K</kbd>
        </button>
        <nav aria-label="Main navigation">
          {navigation.map((group) => (
            <div className="nav-group" key={group.label}>
              <div className="nav-label">{group.label}</div>
              {group.items.map((item) => (
                <Link
                  key={item.href}
                  onClick={() => setMobile(false)}
                  className={`nav-item ${current?.href === item.href ? "active" : ""}`}
                  href={item.href}
                >
                  <item.icon size={17} />
                  <span>{item.name}</span>
                  {item.href === "/find" && <span className="nav-new">↗</span>}
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="status-dot" />
          <span>
            Local workspace<small>Private by default</small>
          </span>
          <ShieldCheck size={16} />
        </div>
      </aside>
      <div className="app-body">
        <div className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-button mobile-menu"
              aria-label="Toggle navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={19} />
            </button>
            <span>Workspace</span>
            <ChevronRight size={12} />
            <strong>{current?.name ?? "Evidence"}</strong>
          </div>
          <div className="topbar-actions">
            <span className="live-label">
              <span className="status-dot" /> SOURCE-BACKED DATA
            </span>
            <button
              className="icon-button theme-toggle"
              aria-label="Toggle color theme"
              onClick={() =>
                setTheme(resolvedTheme === "dark" ? "light" : "dark")
              }
            >
              <Sun size={17} className="sun" />
              <Moon size={17} className="moon" />
            </button>
            <a
              className="docs-link"
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
            >
              API docs
              <ArrowUpRight size={13} />
            </a>
          </div>
        </div>
        <main id="main">{children}</main>
      </div>
      {selected.length > 0 && pathname !== "/compare" && (
        <div className="compare-tray">
          <span className="compare-counter">
            <Check size={14} />
            {selected.length}
          </span>
          <span>models selected</span>
          <button className="text-button" onClick={clear}>
            Clear
          </button>
          <Link className="button primary" href="/compare">
            Compare models <ArrowLeftRight size={14} />
          </Link>
        </div>
      )}
      {search && <SearchPalette close={() => setSearch(false)} />}
    </div>
  );
}
