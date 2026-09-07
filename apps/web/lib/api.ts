import type { components } from "./api-schema";

export type Evidence = components["schemas"]["EvidenceView"];
export type Model = components["schemas"]["ModelView"];
export type ModelPage = components["schemas"]["ModelPage"];
export type ModelDetail = components["schemas"]["ModelDetail"];
export type Deployment = components["schemas"]["DeploymentView"];
export type Provider = components["schemas"]["ProviderView"];

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

export function isPrivateLocked(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.status === 401 ||
      (error.status === 503 &&
        error.message.startsWith("Private API disabled")))
  );
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await response.json();
  if (!response.ok)
    throw new ApiError(
      body.message ?? "The API could not complete this request.",
      response.status,
    );
  return body as T;
}

export type Source = {
  id: string;
  name: string;
  url: string;
  terms_url: string;
  attribution: string;
  status: string;
  last_success_at: string | null;
  interval_seconds: number;
};
export type MarketEvent = {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  model_id: string | null;
  model_name: string | null;
  provider: string | null;
  change_field: string | null;
  title: string;
  old_value: unknown;
  new_value: unknown;
  importance: string;
  detected_at: string;
  source: string;
  source_url: string;
};
export type WatchlistItem = {
  model_id: string;
  model_name: string;
  identity_status: string;
  created_at: string;
};
export type WatchlistState = {
  telegram_configured: boolean;
  items: WatchlistItem[];
};
export type Overview = {
  models: number;
  unresolved_models: number;
  deployments: number;
  providers: number;
  observations: number;
  sources: Source[];
  recent_models: Model[];
  recent_events: MarketEvent[];
};
export type Benchmark = {
  id: string;
  model_id: string;
  model_name: string;
  name: string;
  version: string;
  score: string;
  category: string;
  verification: string;
  evaluator: string;
  source: string;
  source_url: string;
  source_title: string;
  comparable: boolean;
  metric: string;
  group_id: string;
  report_url: string | null;
  reported_date: string | null;
  quality_issues: string[];
};
export type Ranked = {
  deployment: Deployment;
  estimated_cost: string;
  score: string;
  coverage: string;
  confidence: string;
  missing_evidence: string[];
  reason: string;
  assumptions: string[];
};
export type Recommendation = {
  recommended: Ranked | null;
  alternatives: Ranked[];
  fallback_chain: Ranked[];
  eligible_count: number;
  rejected_count: number;
  rejected: { deployment_id: string; model_name: string; reasons: string[] }[];
  warnings: string[];
};
