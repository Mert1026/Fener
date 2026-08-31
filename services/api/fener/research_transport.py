"""Bounded research transport: fixed provider endpoints, no redirects or retries."""

import json
from typing import Any

import httpx

ZAI_SEARCH = "https://api.z.ai/api/paas/v4/web_search"
ZAI_CHAT = "https://api.z.ai/api/paas/v4/chat/completions"


def post_json(endpoint: str, request: dict[str, Any], key: str) -> dict[str, Any]:
    if endpoint not in {ZAI_SEARCH, ZAI_CHAT}:
        raise ValueError("Unsupported research endpoint")
    with httpx.Client(timeout=httpx.Timeout(40, connect=10), follow_redirects=False) as client:
        with client.stream(
            "POST", endpoint, headers={"Authorization": f"Bearer {key}"}, json=request
        ) as response:
            if response.status_code != 200:
                raise ValueError(
                    f"Research provider returned HTTP {response.status_code}. Check credentials, general API access and account limits. No automatic retry was made."
                )
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 1_048_576:
                    raise ValueError("Research response exceeded the size limit.")
            payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Research provider returned an invalid response.")
    return payload
