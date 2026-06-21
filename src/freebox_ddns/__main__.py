"""CLI entry point for the Freebox DynDNS client."""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import sys
from pathlib import Path

from .config import load
from .updater import run


def setup_logging(foreground: bool, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if foreground:
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
        )
    else:
        try:
            handler = logging.handlers.SysLogHandler(address="/dev/log")
        except (OSError, AttributeError):
            # Fallback when /dev/log is unavailable (macOS, container, etc.)
            handler = logging.handlers.SysLogHandler()
        handler.setFormatter(
            logging.Formatter("freebox-ddns[%(process)d]: %(levelname)s %(message)s")
        )

    root.addHandler(handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DynDNS client for LAN hosts behind a Freebox",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("config", type=Path, help="YAML configuration file")
    parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Log to stdout (interactive mode)",
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        metavar="SECONDS",
        help="Polling interval",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    args = parser.parse_args()

    if not args.config.exists():
        parser.error(f"Configuration file not found: {args.config}")

    setup_logging(foreground=args.foreground, verbose=args.verbose)

    config = load(args.config)
    run(config, interval=args.interval)


if __name__ == "__main__":
    main()
