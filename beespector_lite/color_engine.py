"""Small dependency-free byte/text colour classification helpers.

The GUI decides actual colours.  This module only classifies bytes and printable
ASCII runs so it remains unit-testable without Qt.
"""
from __future__ import annotations

PRINTABLE_MIN = 0x20
PRINTABLE_MAX = 0x7E


def byte_class(value: int) -> str:
    value = int(value) & 0xFF
    if value == 0:
        return "nul"
    if value in (9, 10, 13, 32):
        return "space"
    if value < PRINTABLE_MIN or value == 0x7F:
        return "control"
    if value > PRINTABLE_MAX:
        return "non_ascii"
    ch = chr(value)
    if ch.isalpha():
        return "letter"
    if ch.isdigit():
        return "number"
    return "punctuation"


def detected_string_mask(data: bytes, *, minimum: int = 4) -> tuple[bool, ...]:
    """Return one flag per byte for printable ASCII runs of at least *minimum*.

    Runs include ordinary printable ASCII (space through ``~``).  The mask is
    intentionally conservative: controls and high bytes terminate a run.
    """
    if minimum < 1:
        raise ValueError("minimum must be positive")
    mask = [False] * len(data)
    start: int | None = None
    for index, value in enumerate(data + b"\x00"):
        printable = index < len(data) and PRINTABLE_MIN <= value <= PRINTABLE_MAX
        if printable and start is None:
            start = index
        elif not printable and start is not None:
            if index - start >= minimum:
                for pos in range(start, index):
                    mask[pos] = True
            start = None
    return tuple(mask)
