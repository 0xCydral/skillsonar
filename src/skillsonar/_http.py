"""One JSON POST over urllib, shared by the two service clients."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class HttpFailure(Exception):
    """Transport or HTTP error. `status` is 0 when the server was never reached."""

    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


def post_json(url: str, payload: dict, headers: dict | None = None, timeout: float = 120) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        raise HttpFailure(f"HTTP {exc.code}: {body}", exc.code) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HttpFailure(str(getattr(exc, "reason", exc))) from exc
    except ValueError as exc:
        raise HttpFailure(f"response was not JSON: {exc}") from exc
