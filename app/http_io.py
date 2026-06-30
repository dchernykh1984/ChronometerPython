"""HTTP I/O for pushing timing data to the cycling-site API.

WindowsChronometer pushes three streams, each keyed by ``device_id`` (re-posting the
same ``device_id`` overwrites the stored snapshot unless this one is older -- the server
rejects a stale ``client_revision`` with HTTP 409), mirroring the start-list exchange:

* group starts        -> POST /api/v1/group-times/
* finish crossings    -> POST /api/v1/finish-times/   (point 0)
* remote-point cross. -> POST /api/v1/remote-points/  (point_number 1..N)
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def _post(url: str, payload: dict) -> int:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return int(data.get("count", len(payload.get("items", []))))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Connection error: {exc.reason}") from exc
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid response: {exc}") from exc


def upload_group_times(
    site_url: str, token: str, device_id: str, items: list[str], client_revision: int
) -> int:
    """Upload this device's group-start times; returns the count stored."""
    return _post(
        site_url.rstrip("/") + "/api/v1/group-times/",
        {
            "competition_token": token,
            "device_id": device_id,
            "items": items,
            "client_revision": client_revision,
        },
    )


def upload_finish_times(
    site_url: str, token: str, device_id: str, items: list[str], client_revision: int
) -> int:
    """Upload this device's finish (point 0) crossings; returns count stored."""
    return _post(
        site_url.rstrip("/") + "/api/v1/finish-times/",
        {
            "competition_token": token,
            "device_id": device_id,
            "items": items,
            "client_revision": client_revision,
        },
    )


def upload_remote_points(
    site_url: str,
    token: str,
    device_id: str,
    point_number: int,
    items: list[str],
    client_revision: int,
) -> int:
    """Upload this device's crossings for remote control point N (1..N)."""
    return _post(
        site_url.rstrip("/") + "/api/v1/remote-points/",
        {
            "competition_token": token,
            "device_id": device_id,
            "point_number": point_number,
            "items": items,
            "client_revision": client_revision,
        },
    )
