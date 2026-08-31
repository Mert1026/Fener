# Contributing

Use Python 3.12+, Node 24, uv and pnpm. Run `python scripts/manage.py setup` and read the architecture, data model and source contracts before changing ingestion.

- Keep source adapters independent. Validate real upstream shapes, include tiny attributed fixtures, and preserve the original snapshot before normalization.
- Do not merge similarly named models without explicit identity evidence. Preserve serving variants, dates, context differences and provider boundaries.
- Never invent prices, scores, dates or source verification. Unknown values are useful information.
- Use Decimal and native price units. New canonical fields need provenance, freshness behavior and migrations.
- Keep append-only history intact. A source changing A → B → A is three observations, not two.
- Private data must stay out of public endpoints, exports, logs, fixtures and Git.
- Test invariants and user behavior. Add PostgreSQL coverage for database-specific changes. Regenerate the OpenAPI schema after API changes.

Before committing, run `python scripts/manage.py check`, PostgreSQL integration tests, `uv run alembic check`, and inspect `git diff --check`. Use conventional, focused commits. Do not add generated snapshots or a production seed. Do not change the existing license without maintainer direction.

CI validates backend lint/types/tests/migrations, API schema drift, frontend lint/types/tests, formatting and production builds. Browser acceptance should include searching real ingested models, comparison with a chosen deployment, costs, recommendations, evidence inspection, empty states, keyboard navigation, mobile layout and both themes. Record any checks you could not run.
