from fener.models import Model
from sqlalchemy.orm import Session


def test_empty_catalog_and_readiness(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    response = client.get("/api/v1/models")
    assert response.status_code == 200 and response.json()["items"] == []
    assert response.headers["X-Request-ID"]


def test_private_endpoints_fail_closed(client):
    assert client.get("/api/v1/data-health").status_code in {401, 503}
    assert client.post("/api/v1/recommendations", json={}).status_code in {401, 503}


def test_invalid_query_has_consistent_error(client):
    response = client.get("/api/v1/models?limit=10000")
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_input"


def test_empty_recommendation_does_not_fabricate_candidate(client):
    result = client.post("/api/v1/recommendations/preview", json={})
    assert result.status_code == 200
    assert result.json()["recommended"] is None


def test_streamed_oversized_body_is_rejected(client):
    response = client.post(
        "/api/v1/recommendations/preview", content=iter([b"x" * 70000, b"x" * 70000])
    )
    assert response.status_code == 413


def test_search_includes_fresh_unresolved_discoveries(client):
    with Session(client.test_engine) as session:
        session.add(
            Model(
                id="fresh-model",
                identity_key="candidate:source:gpt-6-astra",
                name="gpt-6-astra",
                identity_status="unresolved",
            )
        )
        session.commit()

    assert client.get("/api/v1/models").json()["items"] == []
    result = client.get("/api/v1/models?q=gpt-6").json()
    assert result["total"] == 1
    assert result["items"][0]["identity_status"] == "unresolved"
