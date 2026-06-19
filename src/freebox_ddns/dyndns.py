"""DynDNS2 update protocol (compatible with No-IP, DynDNS, OVH DynHost, etc.)."""

from __future__ import annotations

import logging
from enum import Enum

import httpx

log = logging.getLogger(__name__)

# Success codes as defined by the dyndns2 protocol
_SUCCESS_PREFIXES = ("good", "nochg")


class UpdateResult(Enum):
    SUCCESS = "success"
    TRANSIENT_FAILURE = "transient_failure"
    PERMANENT_FAILURE = "permanent_failure"  # 4xx — do not retry


def update(url: str, login: str, password: str, hostname: str, ip: str) -> UpdateResult:
    """Send a DynDNS2 update request."""
    try:
        r = httpx.get(
            url,
            params={"hostname": hostname, "myip": ip},
            auth=(login, password),
            timeout=15,
            follow_redirects=True,
        )
        r.raise_for_status()
        body = r.text.strip()
        if any(body.startswith(p) for p in _SUCCESS_PREFIXES):
            if body.startswith("nochg"):
                log.debug("%s → %s: unchanged (%s)", hostname, ip, body)
            else:
                log.info("%s → %s: updated (%s)", hostname, ip, body)
            return UpdateResult.SUCCESS
        log.error("%s → %s: unexpected response: %s", hostname, ip, body)
        return UpdateResult.TRANSIENT_FAILURE
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if 400 <= status < 500:
            log.error("%s → %s: HTTP %s (permanent, will not retry)", hostname, ip, status)
            return UpdateResult.PERMANENT_FAILURE
        log.error("%s → %s: HTTP %s", hostname, ip, status)
        return UpdateResult.TRANSIENT_FAILURE
    except Exception as e:
        log.error("%s → %s: %s", hostname, ip, e)
        return UpdateResult.TRANSIENT_FAILURE
