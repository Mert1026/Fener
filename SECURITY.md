# Security and privacy

Fener is currently designed for one trusted local workspace. Bind services to loopback. Do not expose the API, database or development server to the internet. There is no public account system, tenant isolation, production reverse proxy configuration or completed public-release security review.

Private routes require a server-held `FENER_ADMIN_KEY`. Browser unlock uses an HttpOnly, SameSite=Strict signed cookie with an eight-hour expiry verified on the server. HTTPS sessions set Secure. Rotating the administration key invalidates existing sessions. Logout removes the browser cookie; it does not revoke a copied token before expiry. The key is never put into `NEXT_PUBLIC_*` variables or client bundles.

Mutating browser requests must match the HTTP Host and a trusted local origin. `FENER_WEB_ORIGIN` can set one explicit trusted origin for a deliberately configured deployment; it is not a complete production security setup. Source fetches use an HTTPS allowlist, disallow redirects, bound response size and retry politely. POST bodies are bounded even when streamed. API and unlock attempts are rate limited per process; a public deployment needs shared rate limiting and trusted proxy handling.

Model catalogs, source records and benchmark observations are public read data. Harnesses, roles, policies, telemetry, evaluation prompts/outputs, source job queues, identity review notes and persisted recommendations require authentication. Catalog exports use an explicit allowlist that excludes private tables. Raw upstream catalogs are treated as data, not code or instructions. Links are rendered as text/URLs; charts use non-HTML tooltips.

Telemetry accepts token counts, timings, outcomes, costs and optional numeric quality ratings. It rejects prompt/message fields. Evaluation suites and submitted outputs deliberately store private text. Use synthetic or redacted examples when possible and never submit provider secrets as evaluation content.

Policy versions remain drafts until an explicit approval request includes the selected deployment and a review note. Ingestion and recommendations never change defaults. No automatic paid inference, judge-model calls, AI research crawling or outbound notifications are enabled.

Secrets, snapshots, databases, exports and backups are ignored by Git and Docker build contexts. Backups can contain private data and are not encrypted automatically. Protect the workspace with OS permissions and disk encryption. In a fresh non-Windows setup, `.env` is created mode 0600; Windows inherits the user's workspace ACL.

Report vulnerabilities privately to the repository maintainer. Include a minimal redacted reproduction; do not post keys, private prompts, database dumps or exploitable production URLs in public issues.
