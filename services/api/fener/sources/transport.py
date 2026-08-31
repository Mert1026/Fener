import hashlib
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from random import uniform
from typing import Protocol
from urllib.parse import urlparse

import httpx

ALLOWED_HOSTS = {"models.dev", "openrouter.ai", "raw.githubusercontent.com", "api.zeroeval.com"}
MAX_RESPONSE_BYTES = 32 * 1024 * 1024


class SnapshotStore(Protocol):
    def put(self, content: bytes) -> tuple[str, str]: ...
    def get(self, key: str) -> bytes: ...


class LocalSnapshotStore:
    def __init__(self, root: Path):
        self.root = root

    def put(self, content: bytes) -> tuple[str, str]:
        content_hash = hashlib.sha256(content).hexdigest()
        key = f"{content_hash[:2]}/{content_hash}.json"
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != content:
                raise ValueError("Snapshot content-address collision or corrupt object")
        else:
            # Publish only a complete object. A crashed write leaves a temporary
            # file, never a truncated file at the content-addressed key.
            temporary: str | None = None
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
                    temporary = file.name
                    file.write(content)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, path)
            finally:
                if temporary:
                    Path(temporary).unlink(missing_ok=True)
        return content_hash, key

    def get(self, key: str) -> bytes:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("Invalid snapshot path")
        content = path.read_bytes()
        if path.stem != hashlib.sha256(content).hexdigest():
            raise ValueError("Snapshot integrity check failed")
        return content


@dataclass
class FetchResult:
    status: int
    content: bytes
    etag: str | None
    last_modified: str | None


def retry_delay(header: str | None, attempt: int) -> float:
    if header:
        try:
            return max(0, float(header))
        except ValueError:
            try:
                return max(0, (parsedate_to_datetime(header) - datetime.now(UTC)).total_seconds())
            except (ValueError, TypeError):
                pass
    return float(min(30, 2**attempt)) + uniform(0, 0.5)


def fetch(client: httpx.Client, url: str, headers: dict[str, str] | None = None) -> FetchResult:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in ALLOWED_HOSTS
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Source URL is not allowlisted")
    for attempt in range(4):
        try:
            with client.stream(
                "GET", url, headers=headers or {}, follow_redirects=False
            ) as response:
                if response.status_code == 304:
                    return FetchResult(
                        304,
                        b"",
                        response.headers.get("etag"),
                        response.headers.get("last-modified"),
                    )
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 3:
                    delay = retry_delay(response.headers.get("retry-after"), attempt)
                    # Do not retry before long Retry-After deadlines; let the next scheduled run retry.
                    if delay > 60:
                        response.raise_for_status()
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                if response.is_redirect:
                    raise ValueError("Unexpected redirect from source; review allowlist")
                chunks = bytearray()
                for chunk in response.iter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > MAX_RESPONSE_BYTES:
                        raise ValueError("Source response exceeded 32 MiB limit")
                return FetchResult(
                    response.status_code,
                    bytes(chunks),
                    response.headers.get("etag"),
                    response.headers.get("last-modified"),
                )
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == 3:
                raise
            time.sleep(retry_delay(None, attempt))
    raise RuntimeError("Retry loop exhausted")
