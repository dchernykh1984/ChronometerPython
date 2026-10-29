"""HTTP I/O for pushing timing data to the cycling-site API.

WindowsChronometer pushes three streams, each keyed by ``device_id`` (re-posting the
same ``device_id`` overwrites the stored snapshot unless this one is older -- the server
rejects a stale ``client_revision`` with HTTP 409), mirroring the start-list exchange:

* group starts        -> POST /api/v1/group-times/
* finish crossings    -> POST /api/v1/finish-times/   (point 0)
* remote-point cross. -> POST /api/v1/remote-points/  (point_number 1..N)
"""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def fetch_groups(site_url: str, token: str) -> list[str]:
    """Fetch the competition's group names from the cycling site.

    Uses the same participants endpoint the start-list tool reads; the chronometer only
    needs the group names (the ``categories`` list), not their lap counts. The request
    has a 10s timeout so an offline machine fails fast instead of hanging.

    Raises:
        ValueError: on HTTP error, network/timeout error, or an invalid JSON response.
    """
    data = _get_json(site_url, "/api/v1/participants/", token)
    if not isinstance(data, dict):
        raise ValueError("Invalid response: not a JSON object")
    categories = data.get("categories", [])
    if not isinstance(categories, list):
        raise ValueError("Invalid response: categories is not a list")
    groups: list[str] = []
    seen: set[str] = set()
    for cat in categories:
        if not isinstance(cat, dict):
            continue
        name = str(cat.get("name") or "").strip()
        if name and name not in seen:
            seen.add(name)
            groups.append(name)
    return groups


def fetch_start_list(site_url: str, token: str) -> list[str]:
    """Every device's uploaded start protocol lines for a competition, merged.

    The request FinishProtocolGenerator makes: StartProtocolMaker uploads its list
    under its device id, and the site returns them all. An empty list is an error
    here ("nothing uploaded yet"), so a press before the upload cannot wipe a good
    start protocol file.

    Raises:
        ValueError: on HTTP error, network/timeout error, an invalid response, or a
            start list with no lines.
    """
    data = _get_json(site_url, "/api/v1/start-list/", token)
    if not isinstance(data, dict):
        raise ValueError("Invalid response: not a JSON object")
    devices = data.get("devices", [])
    if not isinstance(devices, list):
        raise ValueError("Invalid response: devices is not a list")
    lines: list[str] = []
    for device in devices:
        items = device.get("items") if isinstance(device, dict) else None
        for line in items if isinstance(items, list) else []:
            # Written as they come: anything but one line of text would replace a
            # good start protocol with junk.
            if not isinstance(line, str) or line.splitlines() not in ([line], []):
                raise ValueError("Invalid response: a line is not one line of text")
            if line.strip():  # a blank line is no rider
                lines.append(line)
    if not lines:
        raise ValueError("the site has no start list for this competition yet")
    return lines


def _get_json(site_url: str, path: str, token: str) -> Any:
    """GET a competition's path from the site; the JSON it answers with.

    Raises:
        ValueError: on HTTP error, network/timeout error, or an invalid response.
    """
    url = (
        site_url.rstrip("/")
        + path
        + "?"
        + urllib.parse.urlencode({"competition_token": token})
    )
    return _answer(url)


def _answer(request: str | urllib.request.Request) -> Any:
    """Send one request to the site; the JSON it answers with.

    Raises:
        ValueError: on HTTP error, network/timeout error, or an invalid response.
    """
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Connection error: {exc.reason}") from exc
    except (OSError, http.client.HTTPException) as exc:  # e.g. a timeout mid-answer
        raise ValueError(f"Connection error: {exc}") from exc
    except ValueError as exc:
        raise ValueError(f"Invalid response: {exc}") from exc


def _post(url: str, payload: dict) -> int:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    data = _answer(req)
    try:
        return int(data.get("count", len(payload.get("items", []))))
    except (AttributeError, TypeError, ValueError) as exc:
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
