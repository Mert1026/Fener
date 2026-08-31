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
