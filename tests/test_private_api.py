import pytest
from fener.models import Deployment, Model, Provider
from sqlalchemy.orm import Session

AUTH = {"Authorization": "Bearer test-admin-key"}


@pytest.fixture
def private(client):
    with Session(client.test_engine) as session:
        session.add(Model(id="model", identity_key="canonical:test", name="Fixture model"))
        session.add(Provider(id="provider", name="Fixture provider"))
        session.flush()
        session.add(
            Deployment(
                id="deployment",
                model_id="model",
                access_provider_id="provider",
                api_model_id="test",
                variant="default",
                listing_kind="catalog",
            )
        )
        session.commit()
    client.headers.update(AUTH)
    assert client.post("/api/v1/harnesses", json={"name": "Test harness"}).status_code == 201
    return client


def test_private_telemetry_retry_and_isolation(private):
    harness = private.get("/api/v1/harnesses").json()[0]
    request = {
        "external_run_id": "run-1",
        "harness_id": harness["id"],
        "role_id": harness["roles"][0]["id"],
        "deployment_id": "deployment",
        "task_type": "research",
        "started_at": "2026-08-31T10:00:00Z",
        "duration_ms": 1000,
        "input_tokens": 100,
        "output_tokens": 20,
        "cost": "0.001",
        "success": True,
    }
    first = private.post("/api/v1/telemetry/runs", json=request)
    assert first.status_code == 201
    duplicate = private.post("/api/v1/telemetry/runs", json=request)
    assert duplicate.json() == {"id": first.json()["id"], "duplicate": True}
    assert (
        private.post("/api/v1/telemetry/runs", json={**request, "cost": "0.002"}).status_code == 409
    )
    assert (
        private.post("/api/v1/telemetry/runs", json={**request, "prompt": "private"}).status_code
        == 422
    )
    summary = private.get("/api/v1/harnesses").json()[0]
    assert summary["runs"] == 1 and summary["success_rate"] == 1
    private.headers.pop("Authorization")
    assert private.get("/api/v1/telemetry/runs").status_code == 401
    assert private.get("/api/v1/harnesses").status_code == 401
    assert "Test harness" not in private.get("/api/v1/overview").text


def test_policy_only_changes_default_with_explicit_approval(private):
    role = private.get("/api/v1/harnesses").json()[0]["roles"][0]
    policy = private.post(f"/api/v1/harnesses/roles/{role['id']}/policies", json={}).json()
    assert policy["version"] == 1 and policy["status"] == "draft"
    assert private.get("/api/v1/harnesses").json()[0]["roles"][0]["default_deployment_id"] is None
    url = f"/api/v1/harnesses/policies/{policy['id']}/approve"
    body = {"deployment_id": "deployment", "note": "Reviewed locally"}
    assert private.post(url, json=body).status_code == 422
    assert private.post(url, json={**body, "approve": True}).status_code == 200
    assert private.post(url, json={**body, "approve": True}).status_code == 409
    assert (
        private.get("/api/v1/harnesses").json()[0]["roles"][0]["default_deployment_id"]
        == "deployment"
    )


def test_evaluation_versions_and_exact_case_membership(private):
    suite = {
        "name": "Fixture",
        "version": "1",
        "cases": [
            {"name": "Exact", "input": "Question", "reference": "Answer"},
            {"name": "Human", "input": "Question", "reference": "Rubric", "scorer": "human"},
        ],
    }
    created = private.post("/api/v1/evaluations/suites", json=suite)
    assert created.status_code == 201
    assert private.post("/api/v1/evaluations/suites", json=suite).status_code == 409
    cases = private.get("/api/v1/evaluations").json()["suites"][0]["cases"]
    request = {
        "suite_id": created.json()["id"],
        "deployment_id": "deployment",
        "evaluator_version": "reviewer-1",
        "outputs": [
            {
                "case_id": c["id"],
                "output": "Answer",
                **({"human_score": "0.5"} if c["scorer"] == "human" else {}),
            }
            for c in cases
        ],
    }
    assert (
        private.post(
            "/api/v1/evaluations/runs", json={**request, "outputs": request["outputs"][:1]}
        ).status_code
        == 422
    )
    result = private.post("/api/v1/evaluations/runs", json=request)
    assert result.status_code == 201 and result.json()["score"] == "0.75"
    saved = private.get("/api/v1/evaluations").json()["runs"][0]
    assert saved["evaluator_version"] == "reviewer-1"
    assert all(row["scorer_version"] == "1" for row in saved["results"])


def test_manual_sync_is_durable_and_deduplicated(private):
    first = private.post("/api/v1/internal/sync", json={"source_id": "models_dev"})
    second = private.post("/api/v1/internal/sync", json={"source_id": "models_dev"})
    assert first.status_code == 202 and first.json() == second.json()
    assert len(private.get("/api/v1/internal/sync").json()) == 1
    assert (
        private.post(
            "/api/v1/internal/sync", json={"source_id": "https://malicious.example"}
        ).status_code
        == 422
    )


def test_identity_override_is_scoped_and_audited(private):
    with Session(private.test_engine) as session:
        session.add(
            Model(
                id="target",
                identity_key="canonical:target",
                name="Canonical target",
                identity_status="resolved",
            )
        )
        session.commit()
    response = private.post(
        "/api/v1/internal/deployments/deployment/identity",
        json={
            "target_model_id": "target",
            "evidence_url": "https://example.com/verified-mapping",
            "note": "Reviewed exact API identifier in publisher documentation",
        },
    )
    assert response.status_code == 200
    audit = private.get("/api/v1/internal/identity-overrides").json()[0]
    assert audit["previous_model_id"] == "model" and audit["target_model_id"] == "target"
    with Session(private.test_engine) as session:
        assert session.get(Deployment, "deployment").model_id == "target"
        assert session.get(Model, "model") is not None
