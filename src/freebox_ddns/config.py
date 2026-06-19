from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class DyndnsService:
    url: str
    login: str
    password: str
    hostname: str


@dataclass
class HostConfig:
    freebox_name: str
    services: list[DyndnsService]
    ipv4: bool = True
    ipv6: bool = True


@dataclass
class FreeboxConfig:
    app_id: str = "net.grandou.freebox-ddns"
    app_name: str = "Freebox DDNS"
    app_version: str = "1.0"
    device_name: str = "freebox-ddns"


@dataclass
class Config:
    freebox: FreeboxConfig
    hosts: list[HostConfig]


def load(path: Path) -> Config:
    with open(path) as f:
        data = yaml.safe_load(f)

    fb = data.get("freebox", {})
    freebox = FreeboxConfig(
        app_id=fb.get("app_id", "net.grandou.freebox-ddns"),
        app_name=fb.get("app_name", "Freebox DDNS"),
        app_version=fb.get("app_version", "1.0"),
        device_name=fb.get("device_name", "freebox-ddns"),
    )

    # Shared global services: name → field dict
    global_services: dict[str, dict] = data.get("services", {})

    hosts: list[HostConfig] = []
    for h in data.get("hosts", []):
        services = [
            _resolve_service(s, global_services)
            for s in h.get("services", [])
        ]
        hosts.append(
            HostConfig(
                freebox_name=h["freebox_name"],
                services=services,
                ipv4=h.get("ipv4", True),
                ipv6=h.get("ipv6", True),
            )
        )

    return Config(freebox=freebox, hosts=hosts)


def _resolve_service(entry: dict, global_services: dict[str, dict]) -> DyndnsService:
    """Build a DyndnsService by merging a global service definition with local overrides.

    When `service` is present, the global service fields serve as the base;
    fields defined directly in `entry` take precedence.
    """
    base: dict = {}
    ref = entry.get("service")
    if ref is not None:
        if ref not in global_services:
            raise ValueError(f"Service '{ref}' not found in global services section")
        base = global_services[ref]

    # Merge: base (global) overridden by local fields (excluding the "service" key)
    merged = {**base, **{k: v for k, v in entry.items() if k != "service"}}

    for field in ("url", "login", "password", "hostname"):
        if field not in merged:
            raise ValueError(
                f"Required field '{field}' missing "
                f"{'in service \'' + ref + '\' and' if ref else 'in'} entry {entry}"
            )

    return DyndnsService(
        url=merged["url"],
        login=merged["login"],
        password=merged["password"],
        hostname=merged["hostname"],
    )
