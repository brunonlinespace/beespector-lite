"""Dependency-light inspection helpers for Beespector.

All functions consume bytes from ByteSource and never mutate the source file.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import math
import os
from pathlib import Path
import zlib
from typing import Callable
from .byte_source import ByteSource

MAX_RESULTS = 10_000


def selection_interpretation(data: bytes, total_length: int | None = None) -> dict[str, str]:
    """Return useful read-only interpretations of a selected byte sequence."""
    if not data:
        return {}
    total = len(data) if total_length is None else int(total_length)
    shown = data[:256]
    ascii_text = "".join(chr(b) if 32 <= b <= 126 else "." for b in shown)
    result: dict[str, str] = {
        "Length": f"{total:,} byte{'s' if total != 1 else ''}",
        "Hex": " ".join(f"{b:02X}" for b in shown) + (" …" if total > len(shown) else ""),
        "ASCII": ascii_text + ("…" if total > len(shown) else ""),
    }
    try:
        text = shown.decode("utf-8", "strict")
        if all(ch.isprintable() or ch in "\r\n\t" for ch in text):
            result["UTF-8"] = text + ("…" if total > len(shown) else "")
    except UnicodeDecodeError:
        pass
    if total <= 8 and len(data) == total:
        bits = len(data) * 8
        result[f"Unsigned {bits}-bit LE"] = str(int.from_bytes(data, "little", signed=False))
        result[f"Unsigned {bits}-bit BE"] = str(int.from_bytes(data, "big", signed=False))
        result[f"Signed {bits}-bit LE"] = str(int.from_bytes(data, "little", signed=True))
        result[f"Signed {bits}-bit BE"] = str(int.from_bytes(data, "big", signed=True))
    return result


def range_checksums(source: ByteSource, start: int, length: int, *, chunk_size: int = 1024 * 1024,
                    cancelled: Callable[[], bool] | None = None) -> dict[str, str] | None:
    if start < 0 or length < 0 or start + length > source.size:
        raise ValueError("checksum range is outside the file")
    sha = hashlib.sha256(); md5 = hashlib.md5(); crc = 0
    pos = start; remaining = length
    while remaining:
        if cancelled and cancelled():
            return None
        data = source.read(pos, min(chunk_size, remaining))
        if not data: break
        sha.update(data); md5.update(data); crc = zlib.crc32(data, crc)
        pos += len(data); remaining -= len(data)
    return {"SHA-256": sha.hexdigest(), "MD5": md5.hexdigest(), "CRC32": f"{crc & 0xFFFFFFFF:08X}"}


def range_entropy(source: ByteSource, start: int, length: int, *, chunk_size: int = 1024 * 1024,
                  cancelled: Callable[[], bool] | None = None) -> float | None:
    if start < 0 or length < 0 or start + length > source.size:
        raise ValueError("entropy range is outside the file")
    counts = [0] * 256; total = 0; pos = start; remaining = length
    while remaining:
        if cancelled and cancelled(): return None
        data = source.read(pos, min(chunk_size, remaining))
        if not data: break
        total += len(data)
        for value, count in Counter(data).items(): counts[value] += count
        pos += len(data); remaining -= len(data)
    if total == 0: return 0.0
    return -sum((c/total) * math.log2(c/total) for c in counts if c)


def entropy_description(value: float) -> str:
    if value < 1.0: return "Very low — strongly repetitive / sparse-looking data"
    if value < 4.0: return "Low — limited byte variety"
    if value < 6.5: return "Moderate — structured data is plausible"
    if value < 7.5: return "High — dense or compressed-looking data"
    return "Very high — data may be compressed or encrypted"


def find_printable_strings(source: ByteSource, minimum: int = 4, *, max_results: int = MAX_RESULTS,
                           chunk_size: int = 1024 * 1024, preview_bytes: int = 512,
                           cancelled: Callable[[], bool] | None = None) -> list[tuple[int, int, bytes]]:
    """Find printable ASCII runs without retaining arbitrarily large strings in RAM.

    Each result is (offset, total_length, preview_bytes).  preview_bytes is
    bounded even when the source contains a multi-gigabyte printable run.
    """
    if minimum < 2: minimum = 2
    preview_bytes=max(16,min(int(preview_bytes),4096))
    results: list[tuple[int, int, bytes]] = []
    preview = bytearray(); run_start = 0; run_length = 0
    pos = 0
    def finish():
        nonlocal run_length, preview
        if run_length >= minimum and len(results) < max_results:
            results.append((run_start, run_length, bytes(preview)))
        run_length=0; preview.clear()
    while pos < source.size and len(results) < max_results:
        if cancelled and cancelled(): break
        data = source.read(pos, min(chunk_size, source.size-pos))
        if not data: break
        for i, b in enumerate(data):
            absolute = pos + i
            if 32 <= b <= 126:
                if run_length == 0: run_start = absolute
                run_length += 1
                if len(preview) < preview_bytes: preview.append(b)
            else:
                finish()
                if len(results) >= max_results: break
        pos += len(data)
    if len(results) < max_results: finish()
    return results


def find_repeated_runs(source: ByteSource, minimum: int = 16, *, max_results: int = MAX_RESULTS,
                       chunk_size: int = 1024 * 1024,
                       cancelled: Callable[[], bool] | None = None) -> list[tuple[int, int, int]]:
    """Return (offset, byte_value, run_length) for repeated-byte runs."""
    minimum = max(2, int(minimum)); results: list[tuple[int, int, int]] = []
    current: int | None = None; run_start = 0; run_length = 0; pos = 0
    while pos < source.size and len(results) < max_results:
        if cancelled and cancelled(): break
        data = source.read(pos, min(chunk_size, source.size-pos))
        if not data: break
        for i, b in enumerate(data):
            absolute = pos + i
            if current is None:
                current = b; run_start = absolute; run_length = 1
            elif b == current:
                run_length += 1
            else:
                if run_length >= minimum:
                    results.append((run_start, current, run_length))
                    if len(results) >= max_results: break
                current = b; run_start = absolute; run_length = 1
        pos += len(data)
    if len(results) < max_results and current is not None and run_length >= minimum:
        results.append((run_start, current, run_length))
    return results


def export_range(source: ByteSource, start: int, length: int, target: str | Path, *, chunk_size: int = 1024*1024,
                 progress: Callable[[int,int], None] | None = None,
                 cancelled: Callable[[], bool] | None = None) -> None:
    """Export a selected byte range to a new file without modifying source."""
    if start < 0 or length < 0 or start + length > source.size:
        raise ValueError("export range is outside the file")
    target_path=Path(target).expanduser()
    try:
        if target_path.resolve() == source.path.resolve():
            raise ValueError("The export target cannot be the source file.")
    except OSError:
        pass
    temp=target_path.with_name(target_path.name+".beespector.tmp")
    pos=start; remaining=length
    try:
        with open(temp,"wb") as out:
            while remaining:
                if cancelled and cancelled(): raise InterruptedError("Export cancelled")
                data=source.read(pos,min(chunk_size,remaining))
                if not data: break
                out.write(data); pos += len(data); remaining -= len(data)
                if progress: progress(length-remaining,length)
        if remaining: raise OSError("Could not read the complete selection")
        os.replace(temp,target_path)
    except Exception:
        try: temp.unlink(missing_ok=True)
        except OSError: pass
        raise
