# Fener visual evolution — September 8, 2026

## Audit and direction

The existing product defines its identity through navy `#002d72`, yellow
`#ffd60a`, aqua analytical accents, the Fener mark, and source-first language.
Navigation, canonical-model versus deployment distinctions, evidence links,
and explicit unknown values are valuable foundations and remain recognizable.

The audit covered all 10 main routes plus model, provider, and evidence detail
views. The previous presentation used small labels, similarly weighted panels,
prominent gradients and glowing scatter points. The overview exposed a partial
catalog without enough analytical explanation. Provider cards lacked a useful
aggregate comparison. Settings and benchmark controls left avoidable empty space.

The coherent direction is an evidence desk: strong readable headings, restrained
surface depth, yellow reserved for focus, analytical sections with narrative
context, and exact evidence one interaction away. The existing terminal identity
is developed rather than replaced.

## Implemented

- A shared token and presentation pass for navigation, headers, surfaces,
  tables, forms, tabs, dialogs, evidence, loading, empty, and error states.
  Both themes retain navy and yellow; chart colors have separate light values.
- An overview intelligence brief covering canonical catalog scope, unresolved
  source identities, and the actual last-sync outcomes.
- Catalog analysis on the overview and filtered model pages: known-price median,
  context distribution, and selectable reported-capability coverage. Denominators
  refer to the loaded selection, never the full catalog unless fully supplied.
- Provider listing concentration with direct drill-down. Catalog breadth is
  explicitly distinguished from market share or traffic.
- Expandable serving-evidence coverage wherever deployment tables appear.
- Market-feed event composition, with observation dates and loaded-feed scope.
- Benchmark score distribution restricted to one comparable metric, version,
  evaluator and group; source-extracted scores remain explicitly unverified.
- Refined scatter axes, scoped caption, tooltips, reduced-motion-aware animation,
  existing zoom/pan controls, and an accessible table of plotted models.
- Selectable price-history series, observation dates, and an exact-value table.
  Full deployment identifiers identify groups internally; shortened identifiers
  distinguish their visible legend labels.
- A more compact benchmark control area and a two-column desktop settings layout.
- Mobile navigation state semantics and a dismissible navigation backdrop.

The presentation uses existing API responses. No fictional trends, forecasts,
quality scores, comparisons, or production seed data were introduced. Backend,
database schema, authentication boundaries, ingestion rules, and research
approval flows were not rewritten.

## Findings resolved during verification

1. A long evidence snapshot identifier overflowed the phone viewport. Evidence
   prose now wraps identifiers while keeping the source record readable.
2. Visually hidden table labels could contribute to document overflow on tablets.
   The table scroll region now establishes their positioning context. The new
   browser regression failed at 1026px document width for a 768px viewport, then
   passed at 768px after the fix. Tables retain their own horizontal scrolling.
3. Cost calculation offered a no-op when all compared models had no deployments.
   It is now disabled with a direct explanation. The regression was observed
   failing before the fix and passing afterward.
4. The existing live-data cost test selected the first alphabetical records,
   which currently lack deployments. It now selects two real deployed models,
   and waits for the debounced search to commit before navigating. Cost request,
   response, and result assertions remain intact.

## Executed verification

Scope: working tree on `feat/model-intelligence-platform`, based on `6cea56a`.
Changes are intentionally uncommitted for review.

| Gate                                      | Result     | Evidence                                                                                                                                    |
| ----------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Baseline frontend tests                   | PASS       | 33 tests / 11 files before implementation                                                                                                   |
| Final frontend tests                      | PASS       | `pnpm --filter @fener/web test`: 41 tests / 13 files                                                                                        |
| End-to-end flows                          | PASS       | 6 Playwright tests, real local catalog, headless Microsoft Edge                                                                             |
| Types and production build                | PASS       | `pnpm --filter @fener/web build`, including TypeScript and all 14 generated static pages                                                    |
| Lint                                      | PASS       | `pnpm --filter @fener/web lint`                                                                                                             |
| Changed-file formatting                   | PASS       | Prettier check of every changed frontend file                                                                                               |
| Patch whitespace                          | PASS       | `git diff --check`                                                                                                                          |
| Main-route visual review                  | PASS       | Screenshots of 13 routes at 1440px in both themes and 390px on mobile; no page errors                                                       |
| Additional responsive checks              | PASS       | Overview, catalog, providers, benchmarks, finder, settings at 768, 1024, 1920 and 2560px; no document overflow after the table fix          |
| Private authenticated operations          | UNVERIFIED | Private gates and existing research component tests checked; no paid research or private mutations executed for visual QA                   |
| Cross-browser accessibility certification | UNVERIFIED | Edge keyboard flows, semantics, readable values, and reduced-motion handling reviewed; no claim of an exhaustive assistive-technology audit |
| Deployment                                | UNVERIFIED | Local build and preview only; no remote publication requested                                                                               |

Playwright used `.tmp/design-audit/playwright.config.mjs` to select the installed
Edge browser because the configured Playwright Chromium binary is absent. The
repository's production/test dependencies and browser configuration were not
changed to accommodate this machine.

## Rendered design review

Screenshots and local QA scripts are retained under `.tmp/design-audit/` (ignored).
The before screenshot is `before.png`; final overview images are
`final-dark-overview.png` and `final-light-overview.png`. Route contact sheets,
phone captures, and empty/loading/error captures accompany them.

- Composition and hierarchy: the brief introduces the overview; catalog,
  providers and benchmarks expose different forms of contextual analysis.
- Density and spacing: metrics are integrated into the canvas, table labels are
  enlarged, and deployment coverage uses progressive disclosure.
- Proportions and typography: headings and metrics lead, labels remain legible,
  and mobile layouts stack instead of scaling desktop content down.
- Brand and visual emphasis: navy navigation, yellow focus, and restrained aqua
  analytics remain recognizable in both themes.
- Empty and loading weight: explicit placeholders preserve the page structure;
  empty views explain the next step without synthetic charts.
- Interaction: table selections, calculation, theme switching, phone navigation,
  chart zoom/reset, breakdown keyboard selection, and history series toggles
  passed browser tests.

Source freshness remains an operational limitation: the existing local catalog
is populated, but scheduled source fetches failed under restricted network
access during preview. The UI reports their actual failed state and retains the
last successful timestamps rather than claiming fresh data.
