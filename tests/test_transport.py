import httpx
import pytest
from fener.sources.transport import LocalSnapshotStore, fetch


def test_snapshot_integrity_and_path_boundary(tmp_path):
    store = LocalSnapshotStore(tmp_path)
    _, key = store.put(b'{"test": true}')
    assert store.get(key) == b'{"test": true}'
    with pytest.raises(ValueError, match="path"):
        store.get("../outside.json")
    (tmp_path / key).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        store.get(key)
    with pytest.raises(ValueError, match="corrupt"):
        store.put(b'{"test": true}')


def test_conditional_fetch_and_ssrf_boundary():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(304, headers={"etag": "revision-1"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = fetch(client, "https://models.dev/api.json", {"If-None-Match": "revision-1"})
        assert result.status == 304 and result.content == b""
        assert requests[0].headers["if-none-match"] == "revision-1"
        with pytest.raises(ValueError):
            fetch(client, "http://127.0.0.1/internal")
        with pytest.raises(ValueError):
            fetch(client, "https://models.dev:8443/admin")
    assert len(requests) == 1


def test_retry_after_is_respected(monkeypatch):
    delays = []
    monkeypatch.setattr("fener.sources.transport.time.sleep", delays.append)
    responses = iter(
        [httpx.Response(429, headers={"retry-after": "3"}), httpx.Response(200, json={})]
    )
    with httpx.Client(transport=httpx.MockTransport(lambda _: next(responses))) as client:
        assert fetch(client, "https://models.dev/api.json").status == 200
    assert delays == [3]
