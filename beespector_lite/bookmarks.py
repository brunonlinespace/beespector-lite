"""Privacy-preserving bookmark storage for Beespector.

No inspected pathname is stored.  Files are identified by a content-derived
fingerprint (size + first/last blocks).  Bookmark data lives in a separate
bookmarks.json database beside, not inside, the ordinary preferences file.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, os
from pathlib import Path
from .byte_source import ByteSource
from .settings import config_path

BLOCK = 64 * 1024
MAX_LABEL = 200
MAX_BOOKMARKS_PER_FILE = 1000


def bookmarks_path() -> Path:
    return config_path().with_name("bookmarks.json")


def source_fingerprint(source: ByteSource) -> str:
    digest = hashlib.sha256()
    digest.update(b"Beespector bookmark fingerprint v1\0")
    digest.update(str(source.size).encode("ascii")); digest.update(b"\0")
    first = source.read(0, min(BLOCK, source.size)); digest.update(first)
    if source.size > BLOCK:
        last_start = max(0, source.size - BLOCK); digest.update(source.read(last_start, source.size-last_start))
    return digest.hexdigest()


@dataclass(frozen=True)
class Bookmark:
    offset: int
    label: str = ""


class BookmarkStore:
    def __init__(self, path: Path | None = None):
        self.path = path or bookmarks_path(); self.data = self._load()
    def _load(self) -> dict:
        try: raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError): raw = {}
        return raw if isinstance(raw, dict) else {}
    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True)+"\n", encoding="utf-8"); os.replace(tmp, self.path)
    def list(self, fingerprint: str, size: int) -> list[Bookmark]:
        node = self.data.get(fingerprint, {})
        if not isinstance(node, dict) or int(node.get("size", -1)) != int(size): return []
        rows = node.get("bookmarks", []); out=[]
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    try:
                        off=int(row.get("offset")); label=str(row.get("label", ""))[:MAX_LABEL]
                        if 0 <= off < size: out.append(Bookmark(off,label))
                    except Exception: pass
        return sorted(out, key=lambda b: b.offset)
    def add(self, fingerprint: str, size: int, offset: int, label: str=""):
        rows=self.list(fingerprint,size); label=str(label or "")[:MAX_LABEL]
        rows=[b for b in rows if b.offset != offset]; rows.append(Bookmark(offset,label)); rows=sorted(rows,key=lambda b:b.offset)[:MAX_BOOKMARKS_PER_FILE]
        self.data[fingerprint]={"size":int(size),"bookmarks":[{"offset":b.offset,"label":b.label} for b in rows]}; self._save()
    def remove(self, fingerprint: str, size: int, offset: int):
        rows=[b for b in self.list(fingerprint,size) if b.offset != offset]
        if rows: self.data[fingerprint]={"size":int(size),"bookmarks":[{"offset":b.offset,"label":b.label} for b in rows]}
        else: self.data.pop(fingerprint,None)
        self._save()
    def clear(self, fingerprint: str):
        self.data.pop(fingerprint,None); self._save()
