"""Dependency-free byte/text search helpers."""
from __future__ import annotations
import re
from typing import Callable
from .byte_source import ByteSource

_HEX_SEPARATORS = re.compile(r"[\s,:;_-]+")
MAX_PATTERN_BYTES = 1024 * 1024

def parse_hex_pattern(text: str) -> bytes:
    cleaned = text.strip().replace("0x", "").replace("0X", "")
    cleaned = _HEX_SEPARATORS.sub("", cleaned)
    if not cleaned:
        raise ValueError("Enter one or more hexadecimal bytes.")
    if len(cleaned) % 2:
        raise ValueError("Hex input must contain complete byte pairs.")
    if not re.fullmatch(r"[0-9A-Fa-f]+", cleaned):
        raise ValueError("Hex input may contain only 0-9 and A-F byte pairs.")
    result = bytes.fromhex(cleaned)
    if len(result) > MAX_PATTERN_BYTES:
        raise ValueError("Search patterns are limited to 1 MiB.")
    return result

def encode_text_pattern(text: str) -> bytes:
    if not text:
        raise ValueError("Enter text to find.")
    result = text.encode("utf-8")
    if len(result) > MAX_PATTERN_BYTES:
        raise ValueError("Search patterns are limited to 1 MiB.")
    return result

def find_forward(source: ByteSource, pattern: bytes, start: int = 0, *, chunk_size: int = 1024*1024,
                 cancelled: Callable[[], bool] | None = None) -> int | None:
    if not pattern:
        raise ValueError("pattern cannot be empty")
    start = max(0, min(start, source.size))
    overlap = max(0, len(pattern)-1)
    pos = start
    tail = b""
    while pos < source.size:
        if cancelled and cancelled():
            return None
        data = source.read(pos, min(chunk_size, source.size-pos))
        if not data:
            break
        combined = tail + data
        base = pos - len(tail)
        idx = combined.find(pattern)
        if idx >= 0:
            absolute = base + idx
            if absolute >= start:
                return absolute
        tail = combined[-overlap:] if overlap else b""
        pos += len(data)
    return None

def find_backward(source: ByteSource, pattern: bytes, start: int | None = None, *, chunk_size: int = 1024*1024,
                  cancelled: Callable[[], bool] | None = None) -> int | None:
    if not pattern:
        raise ValueError("pattern cannot be empty")
    if source.size == 0:
        return None
    boundary = source.size if start is None else max(0, min(start, source.size))
    overlap = max(0, len(pattern)-1)
    while boundary > 0:
        if cancelled and cancelled():
            return None
        block_start = max(0, boundary - chunk_size)
        block_end = min(source.size, boundary + overlap)
        data = source.read(block_start, block_end-block_start)
        limit = boundary - block_start
        idx = data.rfind(pattern, 0, limit + len(pattern)-1)
        while idx >= 0 and block_start + idx >= boundary:
            idx = data.rfind(pattern, 0, idx)
        if idx >= 0:
            return block_start + idx
        boundary = block_start
    return None


def find_all(source: ByteSource, pattern: bytes, start: int = 0, *, max_results: int = 10_000,
             chunk_size: int = 1024*1024, cancelled: Callable[[], bool] | None = None) -> list[int]:
    """Find all (including overlapping) occurrences up to max_results."""
    if not pattern:
        raise ValueError("pattern cannot be empty")
    start=max(0,min(start,source.size)); overlap=max(0,len(pattern)-1); pos=start; tail=b""; results=[]; last_added=-1
    while pos < source.size and len(results) < max_results:
        if cancelled and cancelled(): break
        data=source.read(pos,min(chunk_size,source.size-pos))
        if not data: break
        combined=tail+data; base=pos-len(tail); idx=0
        while True:
            idx=combined.find(pattern,idx)
            if idx < 0: break
            absolute=base+idx
            if absolute >= start and absolute != last_added:
                results.append(absolute); last_added=absolute
                if len(results) >= max_results: break
            idx += 1
        tail=combined[-overlap:] if overlap else b""; pos += len(data)
    return results
