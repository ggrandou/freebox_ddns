# freebox-ddns

DynDNS client for hosts behind a Freebox — polls the Freebox API for WAN and LAN IPv6 addresses and updates any DynDNS2-compatible provider.

## How it works

- Polls the Freebox API every 60 seconds (configurable).
- Fetches the WAN IPv4 and IPv6 from the connection status.
- Fetches the LAN IPv6 of each configured host from the Freebox LAN API.
- Sends a DynDNS2 update request only when an address changes.
- IPv4 and IPv6 are acknowledged independently: a transient failure on one does not block the other.

The reserved name `freebox` designates the Freebox router itself; its WAN IPv6 is read from the connection status rather than the LAN host list.

## Installation

Requires Python 3.11+.

```sh
pip install git+https://github.com/ggrandou/freebox-ddns.git
```

Or in development mode:

```sh
. ./setup_env.sh
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and edit it.

Global services (shared across hosts) are defined once under `services:` and referenced by name. Individual hosts can override any field.

```yaml
services:
  infomaniak:
    url: "https://infomaniak.com/nic/update"
    login: "my-login"
    password: "my-password"

hosts:
  - freebox_name: "my-pc"
    ipv4: true
    ipv6: true
    services:
      - service: infomaniak
        hostname: "my-pc.example.com"

  # The Freebox router itself (WAN IPv4 + WAN IPv6)
  - freebox_name: "freebox"
    ipv4: true
    ipv6: true
    services:
      - service: infomaniak
        hostname: "freebox.example.com"
```

See `config.example.yaml` for a full example with multiple providers and per-host overrides.

## Usage

```
freebox-ddns config.yaml [options]

Options:
  -f, --foreground    Log to stdout instead of syslog
  -i, --interval SEC  Polling interval in seconds (default: 60)
  -v, --verbose       Enable DEBUG-level logging
```

## First run

On the first launch the daemon requests authorization on the Freebox screen. Follow the instructions printed to the log, then restart.

## Deployment on OpenWrt

Clone the repository and install dependencies into a local venv:

```sh
cd /opt
git clone https://github.com/ggrandou/freebox-ddns.git freebox_ddns
cd freebox_ddns
./setup_env.sh
cp config.example.yaml config.yaml
# edit config.yaml
```

Install and enable the init script:

```sh
cp openwrt/freebox-ddns /etc/init.d/freebox-ddns
chmod +x /etc/init.d/freebox-ddns
service freebox-ddns enable
service freebox-ddns start
```

The init script points to `/opt/freebox_ddns/.venv/bin/freebox-ddns` and uses procd with `respawn` to automatically restart the daemon on failure.

## Dependencies

- [`python-freebox`](https://github.com/ggrandou/python-freebox) — Freebox API client
- [`httpx`](https://www.python-httpx.org/) ≥ 0.27
- [`pyyaml`](https://pypi.org/project/PyYAML/) ≥ 6

## License

GPL-3.0-or-later
