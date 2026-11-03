"""Bounded, read-only metadata inspection helpers for Beespector.

The functions in this module never modify the inspected source. Embedded-format
inspection is intentionally conservative and bounded: unknown or unsupported
files still return universal filesystem/identification information.
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime
try:
    import grp
except ImportError:  # Windows
    grp = None
import mimetypes
import os
from pathlib import Path
try:
    import pwd
except ImportError:  # Windows
    pwd = None
import stat
import struct
from typing import Any

from .byte_source import ByteSource
from .signatures import identify_source, offset_text, extensions_text

MAX_METADATA_READ = 2 * 1024 * 1024


def _iso_timestamp(value: float | None) -> str:
    if value is None:
        return "Unavailable"
    try:
        return datetime.datetime.fromtimestamp(value).astimezone().isoformat(timespec="seconds")
    except Exception:
        return str(value)


def _safe_owner(uid: int) -> str:
    if pwd is None: return str(uid)
    try:
        return pwd.getpwuid(uid).pw_name
    except Exception:
        return str(uid)


def _safe_group(gid: int) -> str:
    if grp is None: return str(gid)
    try:
        return grp.getgrgid(gid).gr_name
    except Exception:
        return str(gid)


def _xattr_value(value: bytes, limit: int = 256) -> str:
    raw = bytes(value[:limit])
    suffix = "…" if len(value) > limit else ""
    try:
        text = raw.decode("utf-8")
        if text and all(ch.isprintable() or ch in "\t\r\n" for ch in text):
            return text.replace("\n", "\\n") + suffix
    except UnicodeDecodeError:
        pass
    return raw.hex(" ").upper() + suffix


def filesystem_metadata(source: ByteSource) -> list[tuple[str, str]]:
    """Return universal filesystem information without following write paths."""
    path = source.path
    st = os.stat(path, follow_symlinks=True)
    uid=getattr(st,"st_uid",None); gid=getattr(st,"st_gid",None)
    rows = [
        ("Path", str(path)),
        ("Filename", path.name),
        ("Extension", path.suffix or "None"),
        ("Size", f"{source.size:,} bytes"),
        ("Modified", _iso_timestamp(st.st_mtime)),
        ("Accessed", _iso_timestamp(st.st_atime)),
        ("Permissions", f"{stat.filemode(st.st_mode)} ({stat.S_IMODE(st.st_mode):04o})"),
        ("Owner", f"{_safe_owner(uid)} (UID {uid})" if uid is not None else "Unavailable"),
        ("Group", f"{_safe_group(gid)} (GID {gid})" if gid is not None else "Unavailable"),
        ("Inode", str(getattr(st,"st_ino","Unavailable"))),
        ("Device", str(getattr(st,"st_dev","Unavailable"))),
        ("Hard links", str(getattr(st,"st_nlink","Unavailable"))),
        ("Access mode", "READ ONLY (O_RDONLY)"),
        ("No-atime request", "Used" if source.used_noatime else "Not available / not permitted"),
    ]
    # Birth/creation time is platform-dependent. st_birthtime is available on
    # some BSD/macOS filesystems; Windows st_ctime is creation time.
    birth = getattr(st, "st_birthtime", None)
    if birth is not None:
        rows.insert(5, ("Created", _iso_timestamp(birth)))
    elif os.name == "nt":
        rows.insert(5, ("Created", _iso_timestamp(st.st_ctime)))
    else:
        rows.insert(5, ("Changed (metadata)", _iso_timestamp(st.st_ctime)))

    # Preserve symlink information when ByteSource was opened through one.
    original = getattr(source, "original_path", None)
    if original is not None:
        try:
            p = Path(original)
            if p.is_symlink():
                rows.append(("Opened through symlink", str(p)))
                rows.append(("Symlink target", os.readlink(p)))
        except OSError:
            pass

    if hasattr(os, "listxattr") and hasattr(os, "getxattr"):
        try:
            names = sorted(os.listxattr(path, follow_symlinks=True))
        except (OSError, TypeError):
            names = []
        rows.append(("Extended attributes", str(len(names))))
        for name in names[:64]:
            try:
                value = os.getxattr(path, name, follow_symlinks=True)
                rows.append((f"xattr: {name}", _xattr_value(value)))
            except (OSError, TypeError):
                rows.append((f"xattr: {name}", "Unavailable"))
        if len(names) > 64:
            rows.append(("xattr note", f"Showing first 64 of {len(names)} attributes"))
    return rows


def identification_metadata(source: ByteSource) -> list[tuple[str, str]]:
    sig = identify_source(source)
    mime = mimetypes.guess_type(str(source.path))[0] or "application/octet-stream"
    rows = [
        ("Extension", source.path.suffix or "None"),
        ("MIME guess", mime),
        ("Likely signature", sig.name if sig else "Unknown / no built-in match"),
        ("Signature category", sig.category if sig else "Unknown"),
    ]
    if sig:
        rows.extend([
            ("Signature offset", offset_text(sig)),
            ("Signature bytes", sig.pattern.hex(" ").upper()),
            ("Known extensions", extensions_text(sig)),
            ("Signature knowledge", sig.description),
        ])
    return rows


def _png_metadata(source: ByteSource) -> list[tuple[str, str]]:
    head = source.read(0, 33)
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return []
    width, height, bit_depth, colour_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", head[16:29])
    colours = {0:"Grayscale",2:"Truecolour RGB",3:"Indexed colour",4:"Grayscale + alpha",6:"Truecolour RGBA"}
    rows = [
        ("Format", "PNG image"), ("Dimensions", f"{width} × {height}"),
        ("Bit depth", str(bit_depth)), ("Colour type", colours.get(colour_type, str(colour_type))),
        ("Interlace", "Adam7" if interlace == 1 else "None"),
    ]
    # Walk only bounded chunk headers and text metadata; never decode image data.
    pos = 8; counts: dict[str, int] = {}; text_rows = 0
    while pos + 12 <= source.size and pos < MAX_METADATA_READ:
        header = source.read(pos, 8)
        if len(header) < 8: break
        length = struct.unpack(">I", header[:4])[0]; ctype = header[4:8].decode("latin-1", "replace")
        counts[ctype] = counts.get(ctype, 0) + 1
        if ctype == "tEXt" and 0 <= length <= 256 * 1024 and text_rows < 32:
            data = source.read(pos + 8, length)
            if b"\x00" in data:
                key, value = data.split(b"\x00", 1)
                rows.append((f"PNG text: {key.decode('latin-1','replace')[:80]}", value.decode("latin-1","replace")[:500]))
                text_rows += 1
        pos += 12 + length
        if ctype == "IEND": break
        if length > source.size: break
    if counts:
        rows.append(("Chunks", ", ".join(f"{k} × {v}" for k,v in sorted(counts.items()))))
    return rows


def _gif_metadata(source: ByteSource) -> list[tuple[str, str]]:
    data = source.read(0, 13)
    if len(data) < 10 or data[:6] not in (b"GIF87a", b"GIF89a"):
        return []
    width, height = struct.unpack("<HH", data[6:10])
    return [("Format", data[:6].decode("ascii")), ("Dimensions", f"{width} × {height}")]


def _jpeg_metadata(source: ByteSource) -> list[tuple[str, str]]:
    if source.read(0, 3)[:3] != b"\xff\xd8\xff": return []
    rows=[("Format","JPEG image")]; pos=2; scanned=0; exif=False; jfif=None
    sof_markers={0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}
    while pos + 4 <= source.size and scanned < MAX_METADATA_READ:
        b=source.read(pos,2)
        if len(b)<2: break
        if b[0] != 0xFF: pos += 1; scanned += 1; continue
        marker=b[1]; pos += 2; scanned += 2
        if marker in (0xD8,0xD9) or 0xD0 <= marker <= 0xD7: continue
        sizeb=source.read(pos,2)
        if len(sizeb)<2: break
        seglen=struct.unpack(">H",sizeb)[0]
        if seglen < 2: break
        payload_len=seglen-2
        prefix=source.read(pos+2,min(payload_len,32))
        if marker==0xE0 and prefix.startswith(b"JFIF\x00") and len(prefix)>=7:
            jfif=f"{prefix[5]}.{prefix[6]:02d}"
        if marker==0xE1 and prefix.startswith(b"Exif\x00\x00"): exif=True
        if marker in sof_markers and payload_len>=6:
            sof=source.read(pos+2,6)
            if len(sof)>=6:
                precision=sof[0]; height,width=struct.unpack(">HH",sof[1:5]); components=sof[5]
                rows += [("Dimensions",f"{width} × {height}"),("Sample precision",f"{precision} bits"),("Components",str(components))]
                break
        pos += seglen; scanned += seglen
    if jfif: rows.append(("JFIF version",jfif))
    rows.append(("EXIF block", "Present" if exif else "Not detected in bounded header scan"))
    return rows


def _sqlite_metadata(source: ByteSource) -> list[tuple[str, str]]:
    data=source.read(0,100)
    if len(data)<100 or not data.startswith(b"SQLite format 3\x00"): return []
    page_size=struct.unpack(">H",data[16:18])[0]; page_size=65536 if page_size==1 else page_size
    encoding={1:"UTF-8",2:"UTF-16le",3:"UTF-16be"}.get(struct.unpack(">I",data[56:60])[0],"Unknown")
    schema=struct.unpack(">I",data[44:48])[0]
    return [("Format","SQLite 3 database"),("Page size",f"{page_size:,} bytes"),("Text encoding",encoding),("Schema format",str(schema))]


def _elf_metadata(source: ByteSource) -> list[tuple[str, str]]:
    ident=source.read(0,64)
    if len(ident)<20 or ident[:4] != b"\x7fELF": return []
    cls={1:"32-bit",2:"64-bit"}.get(ident[4],"Unknown")
    endian={1:"Little endian",2:"Big endian"}.get(ident[5],"Unknown")
    osabi={0:"System V",3:"Linux",6:"Solaris",9:"FreeBSD"}.get(ident[7],f"ABI {ident[7]}")
    byteorder="little" if ident[5]==1 else "big"
    e_type=int.from_bytes(ident[16:18],byteorder); machine=int.from_bytes(ident[18:20],byteorder)
    types={1:"Relocatable",2:"Executable",3:"Shared object",4:"Core"}
    machines={3:"x86",40:"ARM",62:"x86-64",183:"AArch64",243:"RISC-V"}
    return [("Format","ELF"),("Class",cls),("Endianness",endian),("OS/ABI",osabi),("Object type",types.get(e_type,str(e_type))),("Architecture",machines.get(machine,f"Machine {machine}"))]


def _pe_metadata(source: ByteSource) -> list[tuple[str, str]]:
    if source.read(0,2) != b"MZ": return []
    raw=source.read(0x3C,4)
    if len(raw)<4: return [("Format","DOS MZ executable / possible PE")]
    peoff=struct.unpack("<I",raw)[0]
    head=source.read(peoff,64)
    if len(head)<24 or head[:4] != b"PE\x00\x00": return [("Format","DOS MZ executable")]
    machine, sections, timestamp = struct.unpack("<HHI",head[4:12])
    opt_magic=struct.unpack("<H",head[24:26])[0] if len(head)>=26 else 0
    machines={0x14c:"x86",0x8664:"x86-64",0x1c0:"ARM",0xaa64:"ARM64"}
    rows=[("Format","Windows Portable Executable"),("Architecture",machines.get(machine,f"Machine 0x{machine:04X}")),("Sections",str(sections)),("PE class",{0x10b:"PE32",0x20b:"PE32+"}.get(opt_magic,f"0x{opt_magic:04X}"))]
    if timestamp:
        rows.append(("Link timestamp",_iso_timestamp(timestamp)))
    return rows


def _riff_metadata(source: ByteSource) -> list[tuple[str, str]]:
    head=source.read(0,12)
    if len(head)<12 or head[:4] != b"RIFF": return []
    kind=head[8:12]
    rows=[("Format",f"RIFF/{kind.decode('ascii','replace')}")]
    if kind != b"WAVE": return rows
    pos=12; scanned=0; data_size=None
    while pos+8<=source.size and scanned<MAX_METADATA_READ:
        h=source.read(pos,8)
        if len(h)<8: break
        cid=h[:4]; length=struct.unpack("<I",h[4:8])[0]
        if cid==b"fmt " and length>=16:
            d=source.read(pos+8,16)
            if len(d)>=16:
                fmt,channels,rate,byte_rate,align,bits=struct.unpack("<HHIIHH",d)
                codec={1:"PCM",3:"IEEE float",0xFFFE:"Extensible"}.get(fmt,f"Format {fmt}")
                rows += [("Codec",codec),("Channels",str(channels)),("Sample rate",f"{rate:,} Hz"),("Bits per sample",str(bits)),("Byte rate",f"{byte_rate:,} bytes/s")]
        elif cid==b"data": data_size=length
        pos += 8 + length + (length & 1); scanned += 8 + length + (length & 1)
    if data_size is not None: rows.append(("Audio data",f"{data_size:,} bytes"))
    return rows


def _pdf_metadata(source: ByteSource) -> list[tuple[str, str]]:
    head=source.read(0,min(source.size,MAX_METADATA_READ//2))
    if not head.startswith(b"%PDF-"): return []
    version=head[5:8].decode("ascii","replace")
    tail_start=max(0,source.size-MAX_METADATA_READ//2); tail=source.read(tail_start,min(source.size-tail_start,MAX_METADATA_READ//2))
    blob=head+b"\n"+tail
    rows=[("Format",f"PDF {version}")]
    for key in (b"Title",b"Author",b"Creator",b"Producer",b"CreationDate",b"ModDate"):
        marker=b"/"+key+b" ("; idx=blob.find(marker)
        if idx>=0:
            start=idx+len(marker); end=blob.find(b")",start,min(len(blob),start+1024))
            if end>start:
                rows.append((key.decode("ascii"),blob[start:end].decode("latin-1","replace")[:500]))
    # Best-effort, bounded estimate; explicitly label it as such.
    page_count=blob.count(b"/Type /Page")-blob.count(b"/Type /Pages")
    if page_count>0: rows.append(("Pages (bounded estimate)",str(page_count)))
    return rows


def _zip_metadata(source: ByteSource) -> list[tuple[str, str]]:
    if source.read(0,4) not in (b"PK\x03\x04",b"PK\x05\x06",b"PK\x07\x08"): return []
    # zipfile reads only central directory data here; Beespector does not extract
    # or execute archive members.
    import zipfile
    try:
        with zipfile.ZipFile(source.path,"r") as zf:
            infos=zf.infolist()
            names={i.filename for i in infos}
            subtype="ZIP archive"
            if "mimetype" in names and "META-INF/container.xml" in names: subtype="EPUB/ZIP container"
            elif "[Content_Types].xml" in names and any(n.startswith("word/") for n in names): subtype="DOCX/ZIP container"
            elif "[Content_Types].xml" in names and any(n.startswith("xl/") for n in names): subtype="XLSX/ZIP container"
            elif "mimetype" in names and any(n.startswith("META-INF/") for n in names): subtype="OpenDocument/ZIP container"
            total=sum(i.file_size for i in infos); compressed=sum(i.compress_size for i in infos); encrypted=sum(1 for i in infos if i.flag_bits & 1)
            methods=sorted({i.compress_type for i in infos})
            rows=[("Format",subtype),("Members",f"{len(infos):,}"),("Uncompressed member bytes",f"{total:,}"),("Compressed member bytes",f"{compressed:,}"),("Encrypted members",str(encrypted)),("Compression method IDs",", ".join(map(str,methods)) or "None")]
            if zf.comment: rows.append(("Archive comment",zf.comment[:500].decode("utf-8","replace")))
            # Member names are metadata; show a bounded preview without extracting.
            preview=[i.filename for i in infos[:20]]
            if preview: rows.append(("Member preview", " | ".join(preview) + (" | …" if len(infos)>20 else "")))
            return rows
    except Exception as exc:
        return [("Format","ZIP-family container"),("Archive metadata",f"Could not read central directory: {exc}")]


def embedded_metadata(source: ByteSource) -> list[tuple[str, str]]:
    """Return best-effort format metadata from bounded read-only parsers."""
    parsers=(_png_metadata,_jpeg_metadata,_gif_metadata,_sqlite_metadata,_elf_metadata,_pe_metadata,_riff_metadata,_pdf_metadata,_zip_metadata)
    for parser in parsers:
        try:
            rows=parser(source)
        except Exception as exc:
            return [("Metadata parser",f"{parser.__name__} failed safely: {exc}")]
        if rows:
            return rows
    return [("Embedded metadata","No recognised embedded metadata parser for this file."),
            ("Inspection note","Filesystem, signature, strings, entropy, checksums and raw bytes remain available.")]


def metadata_snapshot(source: ByteSource) -> dict[str, list[tuple[str, str]]]:
    return {
        "Summary": identification_metadata(source),
        "Filesystem": filesystem_metadata(source),
        "Embedded Metadata": embedded_metadata(source),
    }
