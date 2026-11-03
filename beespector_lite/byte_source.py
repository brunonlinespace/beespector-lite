"""Read-only random-access byte source for Beespector.

The source descriptor is opened O_RDONLY. There is intentionally no write API.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import errno
import hashlib
import os
import stat as statmod
import threading
from typing import Callable, Iterator

@dataclass(frozen=True)
class SourceStat:
    device: int
    inode: int
    size: int
    mtime_ns: int
    mode: int

class ByteSource:
    """A regular file opened read-only for positional inspection."""
    def __init__(self, path: str | os.PathLike[str]):
        self.original_path = Path(path).expanduser().absolute()
        self.path = self.original_path.resolve()
        self._fd: int | None = None
        self._stat: SourceStat | None = None
        self.used_noatime = False
        self._seek_lock = threading.RLock()
        self._open()

    def _open(self) -> None:
        flags = os.O_RDONLY
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        noatime = getattr(os, "O_NOATIME", 0)
        fd = None
        if noatime:
            try:
                fd = os.open(self.path, flags | noatime)
                self.used_noatime = True
            except OSError as exc:
                fallbacks = {errno.EPERM, errno.EACCES, errno.EINVAL}
                for name in ("EOPNOTSUPP", "ENOTSUP"):
                    value = getattr(errno, name, None)
                    if value is not None: fallbacks.add(value)
                if exc.errno not in fallbacks:
                    raise
        if fd is None:
            fd = os.open(self.path, flags)
        st = os.fstat(fd)
        if not statmod.S_ISREG(st.st_mode):
            os.close(fd)
            raise ValueError("Beespector opens regular files only; devices, pipes and sockets are refused.")
        self._fd = fd
        self._stat = SourceStat(st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode)

    @property
    def size(self) -> int:
        return 0 if self._stat is None else self._stat.size

    @property
    def mode(self) -> int:
        return 0 if self._stat is None else self._stat.mode

    @property
    def closed(self) -> bool:
        return self._fd is None

    def fileno(self) -> int:
        if self._fd is None:
            raise ValueError("ByteSource is closed")
        return self._fd

    def read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0:
            raise ValueError("offset and length must be non-negative")
        if length == 0 or offset >= self.size:
            return b""
        length = min(length, self.size - offset)
        if hasattr(os, "pread"):
            return os.pread(self.fileno(), length, offset)
        # Windows lacks os.pread. The descriptor remains O_RDONLY; serialize the
        # seek/read pair so random reads cannot race within one ByteSource.
        with self._seek_lock:
            os.lseek(self.fileno(), offset, os.SEEK_SET)
            return os.read(self.fileno(), length)

    def iter_chunks(self, chunk_size: int = 1024 * 1024, *, start: int = 0) -> Iterator[tuple[int, bytes]]:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        pos = max(0, min(start, self.size))
        while pos < self.size:
            data = self.read(pos, min(chunk_size, self.size - pos))
            if not data:
                break
            yield pos, data
            pos += len(data)

    def sha256(self, chunk_size: int = 4 * 1024 * 1024, cancelled: Callable[[], bool] | None = None) -> str | None:
        digest = hashlib.sha256()
        for _, data in self.iter_chunks(chunk_size):
            if cancelled and cancelled():
                return None
            digest.update(data)
        return digest.hexdigest()

    def changed_on_disk(self) -> bool:
        if self._stat is None:
            return False
        try:
            st = os.stat(self.path)
        except OSError:
            return True
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) != (
            self._stat.device, self._stat.inode, self._stat.size, self._stat.mtime_ns
        )

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> "ByteSource":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
