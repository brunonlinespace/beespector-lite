"""Formatting helpers shared by GUI and tests."""
from __future__ import annotations

def human_size(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    value = float(size)
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{size} B"

def as_hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)

def as_compact_hex(data: bytes) -> str:
    return data.hex().upper()

def as_escaped(data: bytes) -> str:
    return "".join(f"\\x{b:02X}" for b in data)

def as_ascii(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in data)
