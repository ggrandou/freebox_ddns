"""Core logic: Freebox polling and DynDNS updates."""

from __future__ import annotations

import ipaddress
import logging
import time

from freebox import Freebox, CredentialStore

from . import dyndns
from .dyndns import UpdateResult
from .config import Config, HostConfig

log = logging.getLogger(__name__)

_UNSET = object()  # sentinel distinct from None to force the first update


def run(config: Config, interval: int = 60) -> None:
    fb = Freebox(
        app_id=config.freebox.app_id,
        app_name=config.freebox.app_name,
        app_version=config.freebox.app_version,
        device_name=config.freebox.device_name,
        store=CredentialStore(config.freebox.app_id),
    )

    log.info("Connecting to Freebox...")
    fb.open()
    log.info("Connected.")

    poller = Poller(fb, config)
    try:
        while True:
            try:
                poller.poll()
            except Exception as e:
                log.error("Polling error: %s", e)
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("Shutting down.")
    finally:
        fb.close()
        log.info("Disconnected.")


class Poller:
    def __init__(self, fb: Freebox, config: Config) -> None:
        self.fb = fb
        self.config = config
        self.last_ipv4: object = _UNSET
        self.last_ipv6: dict[str, object] = {h.freebox_name: _UNSET for h in config.hosts}

    def poll(self) -> None:
        need_ipv4 = any(h.ipv4 for h in self.config.hosts)
        need_ipv6 = any(h.ipv6 for h in self.config.hosts)

        current_ipv4 = self._wan_ipv4() if need_ipv4 else None
        current_ipv6: dict[str, str | None] = {}
        if need_ipv6:
            hosts_lan = self.fb.lan.hosts("pub")
            for host in self.config.hosts:
                if host.ipv6:
                    current_ipv6[host.freebox_name] = self._host_ipv6(hosts_lan, host.freebox_name)

        ipv4_changed = current_ipv4 != self.last_ipv4
        if ipv4_changed:
            log.info(
                "WAN IPv4: %s → %s",
                "(init)" if self.last_ipv4 is _UNSET else self.last_ipv4,
                current_ipv4,
            )

        for host in self.config.hosts:
            cur_v6 = current_ipv6.get(host.freebox_name)
            ipv6_changed = host.ipv6 and cur_v6 != self.last_ipv6[host.freebox_name]

            if ipv6_changed:
                log.info(
                    "%s IPv6: %s → %s",
                    host.freebox_name,
                    "(init)" if self.last_ipv6[host.freebox_name] is _UNSET else self.last_ipv6[host.freebox_name],
                    cur_v6,
                )

            if ipv4_changed or ipv6_changed:
                ipv4_transient, ipv6_transient = self._update_host(
                    host,
                    current_ipv4 if host.ipv4 else None,
                    cur_v6 if host.ipv6 else None,
                )
                # Acknowledge each IP type independently.
                # On transient failure, leave last_* unchanged so the IP still looks new next cycle.
                # On success or permanent failure (4xx), acknowledge to avoid infinite retries.
                if host.ipv4 and not ipv4_transient:
                    self.last_ipv4 = current_ipv4
                if host.ipv6 and not ipv6_transient:
                    self.last_ipv6[host.freebox_name] = cur_v6

    def _wan_ipv4(self) -> str | None:
        status = self.fb.connection.status()
        if status.state != "up":
            log.warning("Freebox connection is not up (state: %s)", status.state)
            return None
        return status.ipv4

    def _host_ipv6(self, hosts_lan: list, name: str) -> str | None:
        """Return the active GUA IPv6 address of a LAN host, or None."""
        for host in hosts_lan:
            if host.primary_name != name:
                continue
            candidates = [
                l3
                for l3 in host.l3connectivities
                if l3.af == "ipv6" and l3.active and _is_gua(l3.addr)
            ]
            if not candidates:
                log.debug("%s: no active GUA IPv6 address found", name)
                return None
            best = max(candidates, key=lambda l3: l3.last_activity)
            return best.addr
        log.warning("Host '%s' not found in Freebox LAN", name)
        return None

    @staticmethod
    def _update_host(host: HostConfig, ipv4: str | None, ipv6: str | None) -> tuple[bool, bool]:
        """Send DynDNS updates for all services of a host.

        Returns (ipv4_transient_failure, ipv6_transient_failure).
        Permanent failures (4xx) are logged but do not set the transient flag.
        """
        ipv4_transient = False
        ipv6_transient = False
        for svc in host.services:
            if ipv4:
                result = dyndns.update(svc.url, svc.login, svc.password, svc.hostname, ipv4)
                if result == UpdateResult.TRANSIENT_FAILURE:
                    ipv4_transient = True
            if ipv6:
                result = dyndns.update(svc.url, svc.login, svc.password, svc.hostname, ipv6)
                if result == UpdateResult.TRANSIENT_FAILURE:
                    ipv6_transient = True
        return ipv4_transient, ipv6_transient


def _is_gua(addr: str) -> bool:
    try:
        return ipaddress.ip_address(addr).is_global
    except ValueError:
        return False
