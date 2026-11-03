#!/usr/bin/env python3
"""Beespector Lite launcher."""
from __future__ import annotations
import sys
from beespector_lite import APP_NAME, APP_VERSION, COMPONENT_ID

# Stable non-executing source-recognition marker for local development tools.
# DEV_DROP_COMPONENT_ID: beespector-lite

def entry(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if "--version" in args:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    if "--component-id" in args:
        print(COMPONENT_ID)
        return 0
    from beespector_lite.app import main as gui_main
    return gui_main(args)

if __name__ == "__main__":
    raise SystemExit(entry())
