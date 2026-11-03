from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True)
class Signature:
    category: str
    name: str
    pattern: bytes
    description: str
    offset: int = 0
    extensions: tuple[str, ...] = ()
    offsets: tuple[int, ...] = ()
    guard: bytes = b""
    guard_offset: int = 0
    auto_detect: bool = True

    def candidate_offsets(self) -> tuple[int, ...]:
        return self.offsets or (self.offset,)


def _b(hex_text: str) -> bytes:
    return bytes.fromhex(hex_text)


def S(category: str, name: str, pattern: str | bytes, description: str, *, offset: int = 0,
      extensions: Iterable[str] = (), offsets: Iterable[int] = (), guard: str | bytes = b"",
      guard_offset: int = 0, auto_detect: bool = True) -> Signature:
    raw = _b(pattern) if isinstance(pattern, str) else bytes(pattern)
    g = _b(guard) if isinstance(guard, str) else bytes(guard)
    return Signature(category, name, raw, description, offset,
                     tuple(e.lower().lstrip('.') for e in extensions), tuple(offsets), g,
                     guard_offset, auto_detect)


# Curated from the Wikipedia "List of file signatures" article (oldid 1369687425,
# reviewed 2026-08-23), with conservative automatic-detection choices.  Weak,
# highly ambiguous or variable-run-in signatures can still appear in the Byte
# Library while auto_detect=False prevents them from becoming false-positive
# file identifications.
SIGNATURES = (
    # Scripts / text / documents
    S("Scripts/Text", "Shebang script", "23 21", "Script/data beginning with a Unix shebang marker.", extensions=("sh","bash","zsh","fish","py","pyw","pl","rb")),
    S("Documents", "PDF document", b"%PDF-", "Portable Document Format header.", extensions=("pdf",)),
    S("Documents", "RTF document", b"{\\rtf1", "Rich Text Format version 1 header.", extensions=("rtf",)),
    S("Documents", "PostScript document", b"%!PS", "PostScript document/program header.", extensions=("ps",)),
    S("Documents", "EPS document", b"%!PS-Adobe-3.", "Encapsulated PostScript family header.", extensions=("eps","epsf")),
    S("Documents", "Windows HtmlHelp CHM", "49 54 53 46 03 00 00 00", "Microsoft Compiled HTML Help container.", extensions=("chm",)),
    S("Documents", "Windows legacy Help", "3F 5F", "Windows 3.x/95/98 Help file signature.", extensions=("hlp",), auto_detect=False),
    S("Documents", "DjVu document marker", b"DJV", "DjVu form marker following AT&TFORM container data.", offset=12, extensions=("djvu","djv"), guard=b"AT&TFORM"),
    S("Documents", "ClarisWorks document", "02 00 5A 57 52 54 00 00 00 00 00 00 00 00 00 00", "ClarisWorks word-processing document.", extensions=("cwk",)),
    S("Documents", "AppleWorks 5 document", "05 07 00 00 42 4F 42 4F", "AppleWorks 5 document header.", extensions=("cwk",)),
    S("Documents", "AppleWorks 6 document", "06 07 E1 00 42 4F 42 4F", "AppleWorks 6 document header.", extensions=("cwk",)),
    S("Documents", "Adobe InDesign document", "06 06 ED F5 D8 1D 46 E5 BD 31 EF E7 FE 74 B7 1D", "Adobe InDesign document magic.", extensions=("indd",)),
    S("Documents", "QuarkXPress — little endian", "00 00 49 49 58 50 52", "QuarkXPress document, little-endian form.", extensions=("qxd",)),
    S("Documents", "QuarkXPress — big endian", "00 00 4D 4D 58 50 52", "QuarkXPress document, big-endian form.", extensions=("qxd",)),
    S("Documents", "OLE Compound File", "D0 CF 11 E0 A1 B1 1A E1", "Microsoft Compound File Binary container used by legacy Office, MSI, MSG and other formats.", extensions=("doc","xls","ppt","msi","msg")),
    S("Documents", "Microsoft Developer Studio project", b"# Microsoft Developer Studio", "Legacy Microsoft Developer Studio project file.", extensions=("dsp",)),
    S("Documents", "Sibelius score", "0F 53 49 42 45 4C 49 55 53", "Sibelius music score file.", extensions=("sib",)),
    S("Documents", "DeskMate document", "0D 44 4F 43", "DeskMate document file.", extensions=("doc",)),
    S("Documents", "DeskMate worksheet", "0E 57 4B 53", "DeskMate worksheet file.", extensions=("wks",)),
    S("Documents", "Zone Identifier", b"[ZoneTransfer]", "Microsoft Zone Identifier alternate data stream content.", extensions=("identifier",)),
    S("Documents", "Email message", b"Received:", "RFC-style email message beginning with a Received header.", extensions=("eml",), auto_detect=False),
    S("Documents", "Environment Modules modulefile", b"#%Module", "Environment Modules modulefile marker."),
    S("Documents", "HL7 message — MSH", b"MSH|", "Health Level Seven message starting with an MSH segment.", extensions=("hl7",)),
    S("Documents", "HL7 message — BSH", b"BSH|", "Health Level Seven batch message starting with a BSH segment.", extensions=("hl7",)),

    # XML / encodings
    S("Encodings", "UTF-8 BOM", "EF BB BF", "UTF-8 byte-order mark.", extensions=("txt","xml")),
    S("Encodings", "UTF-16 LE BOM", "FF FE", "UTF-16 little-endian byte-order mark.", extensions=("txt","xml")),
    S("Encodings", "UTF-16 BE BOM", "FE FF", "UTF-16 big-endian byte-order mark.", extensions=("txt","xml")),
    S("Encodings", "UTF-32 LE BOM", "FF FE 00 00", "UTF-32 little-endian byte-order mark.", extensions=("txt","xml")),
    S("Encodings", "UTF-32 BE BOM", "00 00 FE FF", "UTF-32 big-endian byte-order mark.", extensions=("txt","xml")),
    S("Encodings", "UTF-7 BOM +/v8", "2B 2F 76 38", "One UTF-7 byte-order-mark form."),
    S("Encodings", "UTF-7 BOM +/v9", "2B 2F 76 39", "One UTF-7 byte-order-mark form."),
    S("Encodings", "UTF-7 BOM +/v+", "2B 2F 76 2B", "One UTF-7 byte-order-mark form."),
    S("Encodings", "UTF-7 BOM +/v/", "2B 2F 76 2F", "One UTF-7 byte-order-mark form."),
    S("Encodings", "SCSU BOM", "0E FE FF", "Standard Compression Scheme for Unicode byte-order mark."),
    S("Encodings", "UTF-EBCDIC BOM", "DD 73 66 73", "UTF-EBCDIC byte-order mark."),
    S("Scripts/Text", "XML declaration — 8-bit", b"<?xml ", "XML declaration in UTF-8 or another compatible 8-bit encoding.", extensions=("xml",)),
    S("Scripts/Text", "XML declaration — UTF-16LE", "3C 00 3F 00 78 00 6D 00 6C 00 20 00", "XML declaration encoded UTF-16LE.", extensions=("xml",)),
    S("Scripts/Text", "XML declaration — UTF-16BE", "00 3C 00 3F 00 78 00 6D 00 6C 00 20", "XML declaration encoded UTF-16BE.", extensions=("xml",)),
    S("Scripts/Text", "XML declaration — UTF-32LE", "3C 00 00 00 3F 00 00 00 78 00 00 00 6D 00 00 00 6C 00 00 00 20 00 00 00", "XML declaration encoded UTF-32LE.", extensions=("xml",)),
    S("Scripts/Text", "XML declaration — UTF-32BE", "00 00 00 3C 00 00 00 3F 00 00 00 78 00 00 00 6D 00 00 00 6C 00 00 00 20", "XML declaration encoded UTF-32BE.", extensions=("xml",)),

    # Certificates / keys
    S("Keys/Certificates", "PEM certificate", b"-----BEGIN CERTIFICATE-----", "PEM-encoded X.509 certificate.", extensions=("crt","pem")),
    S("Keys/Certificates", "PEM certificate request", b"-----BEGIN CERTIFICATE REQUEST-----", "PEM-encoded certificate-signing request.", extensions=("csr","pem")),
    S("Keys/Certificates", "PEM PKCS#8 private key", b"-----BEGIN PRIVATE KEY-----", "PEM-encoded PKCS#8 private key.", extensions=("key","pem")),
    S("Keys/Certificates", "PEM RSA private key", b"-----BEGIN RSA PRIVATE KEY-----", "PEM-encoded RSA private key.", extensions=("key","pem")),
    S("Keys/Certificates", "PEM DSA private key", b"-----BEGIN DSA PRIVATE KEY-----", "PEM-encoded DSA private key.", extensions=("key","pem")),
    S("Keys/Certificates", "OpenSSH private key", b"-----BEGIN OPENSSH PRIVATE KEY-----", "OpenSSH private-key file.", extensions=("key",)),
    S("Keys/Certificates", "SSH2 public key", b"-----BEGIN SSH2 PUBLIC KEY-----", "SSH2 public-key file.", extensions=("pub",)),
    S("Keys/Certificates", "PuTTY private key v2", b"PuTTY-User-Key-File-2:", "PuTTY private-key file version 2.", extensions=("ppk",)),
    S("Keys/Certificates", "PuTTY private key v3", b"PuTTY-User-Key-File-3:", "PuTTY private-key file version 3.", extensions=("ppk",)),
    S("Keys/Certificates", "Armored PGP public key", b"-----BEGIN PGP PUBLIC KEY BLOCK-----", "ASCII-armored PGP public key.", extensions=("asc",)),
    S("Keys/Certificates", "Java KeyStore", "FE ED FE ED", "Java KeyStore magic.", extensions=("jks",)),
    S("Keys/Certificates", "Password Safe v3", b"PWS3", "Password Safe / Password Gorilla database header.", extensions=("psafe3",)),

    # Images
    S("Images", "PNG image", "89 50 4E 47 0D 0A 1A 0A", "Portable Network Graphics signature.", extensions=("png",)),
    S("Images", "JPEG image", "FF D8 FF", "JPEG start-of-image marker.", extensions=("jpg","jpeg")),
    S("Images", "GIF87a image", b"GIF87a", "GIF87a image header.", extensions=("gif",)),
    S("Images", "GIF89a image", b"GIF89a", "GIF89a image header.", extensions=("gif",)),
    S("Images", "BMP image", b"BM", "Windows bitmap image header.", extensions=("bmp","dib")),
    S("Images", "TIFF image — little endian", "49 49 2A 00", "TIFF little-endian image header.", extensions=("tif","tiff")),
    S("Images", "TIFF image — big endian", "4D 4D 00 2A", "TIFF big-endian image header.", extensions=("tif","tiff")),
    S("Images", "BigTIFF — little endian", "49 49 2B 00", "BigTIFF little-endian image header.", extensions=("tif","tiff")),
    S("Images", "BigTIFF — big endian", "4D 4D 00 2B", "BigTIFF big-endian image header.", extensions=("tif","tiff")),
    S("Images", "ICO icon", "00 00 01 00", "Windows icon file header.", extensions=("ico",)),
    S("Images", "Apple ICNS icon", b"icns", "Apple Icon Image format header.", extensions=("icns",)),
    S("Images", "Adobe Photoshop PSD", b"8BPS", "Adobe Photoshop document header.", extensions=("psd",)),
    S("Images", "Canon RAW CR2", "49 49 2A 00 10 00 00 00 43 52", "Canon RAW version 2 header, TIFF-derived.", extensions=("cr2",)),
    S("Images", "Canon RAW CR3", b"ftypcrx", "Canon RAW version 3 ISO-base-media brand marker.", offset=4, extensions=("cr3",)),
    S("Images", "Kodak Cineon image", "80 2A 5F D7", "Kodak Cineon image header.", extensions=("cin",)),
    S("Images", "DPX image — big endian", b"SDPX", "SMPTE DPX image, big-endian header.", extensions=("dpx",)),
    S("Images", "DPX image — little endian", b"XPDS", "SMPTE DPX image, little-endian header.", extensions=("dpx",)),
    S("Images", "OpenEXR image", "76 2F 31 01", "OpenEXR image header.", extensions=("exr",)),
    S("Images", "BPG image", "42 50 47 FB", "Better Portable Graphics header.", extensions=("bpg",)),
    S("Images", "JPEG 2000 container", "00 00 00 0C 6A 50 20 20 0D 0A 87 0A", "JPEG 2000 family container signature.", extensions=("jp2","j2k","jpf","jpm","jpg2","j2c","jpc","jpx","mj2")),
    S("Images", "JPEG 2000 codestream", "FF 4F FF 51", "JPEG 2000 codestream start.", extensions=("j2k","j2c","jpc")),
    S("Images", "QOI image", b"qoif", "Quite OK Image Format header.", extensions=("qoi",)),
    S("Images", "FLIF image", b"FLIF", "Free Lossless Image Format header.", extensions=("flif",)),
    S("Images", "WebP image", b"WEBP", "WebP form marker at offset 8 inside a RIFF container.", offset=8, extensions=("webp",), guard=b"RIFF"),
    S("Images", "JPEG XL container", "00 00 00 0C 4A 58 4C 20 0D 0A 87 0A", "JPEG XL container signature.", extensions=("jxl",)),
    S("Images", "JPEG XL codestream", "FF 0A", "JPEG XL raw codestream signature.", extensions=("jxl",)),
    S("Images", "PBM ASCII", "50 31 0A", "Portable bitmap ASCII header.", extensions=("pbm",)),
    S("Images", "PBM binary", "50 34 0A", "Portable bitmap binary header.", extensions=("pbm",)),
    S("Images", "PGM ASCII", "50 32 0A", "Portable graymap ASCII header.", extensions=("pgm",)),
    S("Images", "PGM binary", "50 35 0A", "Portable graymap binary header.", extensions=("pgm",)),
    S("Images", "PPM ASCII", "50 33 0A", "Portable pixmap ASCII header.", extensions=("ppm",)),
    S("Images", "PPM binary", "50 36 0A", "Portable pixmap binary header.", extensions=("ppm",)),
    S("Images", "Windows Metafile", "D7 CD C6 9A", "Windows Metafile header.", extensions=("wmf",)),
    S("Images", "GIMP XCF image", b"gimp xcf", "GIMP XCF image header.", extensions=("xcf",)),
    S("Images", "X PixMap", b"/* XPM */", "X PixMap source marker.", extensions=("xpm",)),
    S("Images", "Radiance HDR image", b"#?RADIANCE\n", "Radiance high-dynamic-range image header.", extensions=("hdr",)),
    S("Images", "HEIF image", b"ftypheic", "HEIF/HEIC brand marker in ISO Base Media container.", offset=4, extensions=("heif","heic")),

    # Archives / compression / packages
    S("Archives", "ZIP archive", "50 4B 03 04", "ZIP local-file header.", extensions=("zip","pk3","pk4")),
    S("Archives", "Empty ZIP archive", "50 4B 05 06", "ZIP end-of-central-directory record, commonly an empty archive.", extensions=("zip",)),
    S("Archives", "Spanned ZIP archive", "50 4B 07 08", "ZIP spanning/data-descriptor marker.", extensions=("zip",)),
    S("Packages", "Android APK / ZIP", "50 4B 03 04", "Android APK uses the ZIP container format.", extensions=("apk",)),
    S("Packages", "Java JAR / ZIP", "50 4B 03 04", "Java JAR uses the ZIP container format.", extensions=("jar",)),
    S("Documents", "EPUB / ZIP", "50 4B 03 04", "EPUB uses the ZIP container format.", extensions=("epub",)),
    S("Documents", "Word OOXML / ZIP", "50 4B 03 04", "Microsoft Word OOXML package uses ZIP.", extensions=("docx",)),
    S("Documents", "Excel OOXML / ZIP", "50 4B 03 04", "Microsoft Excel OOXML package uses ZIP.", extensions=("xlsx",)),
    S("Documents", "PowerPoint OOXML / ZIP", "50 4B 03 04", "Microsoft PowerPoint OOXML package uses ZIP.", extensions=("pptx",)),
    S("Documents", "OpenDocument / ZIP", "50 4B 03 04", "OpenDocument text/spreadsheet/presentation packages use ZIP.", extensions=("odt","ods","odp")),
    S("Packages", "Python wheel / ZIP", "50 4B 03 04", "Python wheel package uses ZIP.", extensions=("whl",)),
    S("Packages", "MSIX / ZIP", "50 4B 03 04", "MSIX application package uses ZIP.", extensions=("msix",)),
    S("Packages", "Firefox XPI / ZIP", "50 4B 03 04", "Mozilla XPI package uses ZIP.", extensions=("xpi",)),
    S("Archives", "RAR 1.5–4.x archive", "52 61 72 21 1A 07 00", "RAR archive signature used by versions before RAR 5.", extensions=("rar",)),
    S("Archives", "RAR 5 archive", "52 61 72 21 1A 07 01 00", "RAR 5 archive signature.", extensions=("rar",)),
    S("Archives", "GZIP archive", "1F 8B", "gzip compressed stream header.", extensions=("gz","tgz")),
    S("Archives", "BZIP2 archive", b"BZh", "bzip2 compressed stream header.", extensions=("bz2",)),
    S("Archives", "XZ archive", "FD 37 7A 58 5A 00", "XZ compressed stream header.", extensions=("xz",)),
    S("Archives", "7-Zip archive", "37 7A BC AF 27 1C", "7-Zip archive signature.", extensions=("7z",)),
    S("Archives", "Zstandard frame", "28 B5 2F FD", "Zstandard compressed-frame magic.", extensions=("zst",)),
    S("Archives", "LZIP archive", b"LZIP", "lzip compressed-file header.", extensions=("lz",)),
    S("Archives", "Unix ar archive", b"!<arch>\n", "Unix ar archive header; Debian packages use this container.", extensions=("a","ar")),
    S("Packages", "Debian package / ar", b"!<arch>\n", "Debian .deb package uses an ar container.", extensions=("deb",)),
    S("Archives", "TAR archive", b"ustar", "POSIX tar archive magic at offset 257.", offset=257, extensions=("tar",)),
    S("Archives", "CPIO new ASCII", b"070701", "cpio new-ASCII archive header.", extensions=("cpio",)),
    S("Archives", "CPIO new ASCII + CRC", b"070702", "cpio new-ASCII archive header with CRC.", extensions=("cpio",)),
    S("Archives", "CPIO old ASCII", b"070707", "cpio old-ASCII archive header.", extensions=("cpio",)),
    S("Archives", "Unix compress — LZW", "1F 9D", "Unix compress stream using LZW.", extensions=("z",)),
    S("Archives", "Unix compress — LZH", "1F A0", "Unix compress stream using LZH.", extensions=("z",)),
    S("Archives", "LZH method 0", b"-lh0-", "LZH archive method marker at offset 2.", offset=2, extensions=("lzh",)),
    S("Archives", "LZH method 5", b"-lh5-", "LZH archive method marker at offset 2.", offset=2, extensions=("lzh",)),
    S("Archives", "RNC compressed v1", "52 4E 43 01", "Rob Northen Compression version 1 stream.", auto_detect=True),
    S("Archives", "RNC compressed v2", "52 4E 43 02", "Rob Northen Compression version 2 stream.", auto_detect=True),
    S("Archives", "LZ4 frame", "04 22 4D 18", "LZ4 frame-format signature.", extensions=("lz4",)),
    S("Archives", "Microsoft CAB", b"MSCF", "Microsoft Cabinet archive header.", extensions=("cab",)),
    S("Archives", "InstallShield CAB", b"ISc(", "InstallShield CAB archive header.", extensions=("cab",)),
    S("Archives", "Windows compressed SZDD", b"SZDD", "Legacy Microsoft compressed-file header.", extensions=("ex_","dl_")),
    S("Archives", "Windows compressed KWAJ", b"KWAJ", "Windows 3.1-era compressed-file header."),
    S("Archives", "ZOO archive", b"ZOO", "Zoo archive signature.", extensions=("zoo",)),
    S("Archives", "ACE archive", b"**ACE**", "ACE archive marker at offset 7.", offset=7, extensions=("ace",)),
    S("Archives", "ARJ archive", "60 EA", "ARJ archive header.", extensions=("arj",)),
    S("Archives", "XAR archive", b"xar!", "eXtensible ARchive header.", extensions=("xar",)),
    S("Archives", "Czip X encrypted archive", b"CZPX", "Czip X encrypted archive header.", extensions=("czx",)),
    S("Archives", "ARC archive", "1A 08", "ARC archive header.", extensions=("arc",)),
    S("Archives", "FreeArc archive", b"ArC", "FreeArc archive header.", extensions=("arc","cdx")),
    S("Archives", "zlib stream — 78 01", "78 01", "Common zlib header (no compression, no preset dictionary).", extensions=("zlib",), auto_detect=False),
    S("Archives", "zlib stream — 78 5E", "78 5E", "Common zlib header (fast compression).", extensions=("zlib",), auto_detect=False),
    S("Archives", "zlib stream — 78 9C", "78 9C", "Common zlib header (default compression).", extensions=("zlib",), auto_detect=False),
    S("Archives", "zlib stream — 78 DA", "78 DA", "Common zlib header (best compression).", extensions=("zlib",), auto_detect=False),
    S("Archives", "LZFSE stream", b"bvx2", "Apple LZFSE compressed stream.", extensions=("lzfse",)),
    S("Packages", "RPM package", "ED AB EE DB", "RPM package lead magic.", extensions=("rpm",)),
    S("Packages", "Amazon Kindle update package", b"SP01", "Amazon Kindle update package header.", extensions=("bin",)),
    S("Packages", "Windows Imaging Format", b"MSWIM\x00\x00\x00", "Windows Imaging Format container.", extensions=("wim","swm","esd")),

    # Executables / bytecode / binary patches
    S("Executables", "ELF executable/object", "7F 45 4C 46", "Executable and Linkable Format header used by Linux and other Unix-like systems.", extensions=("elf","o","out","ko","so","bin")),
    S("Executables", "DOS/Windows MZ executable", b"MZ", "DOS MZ header; Windows PE executables normally begin this way.", extensions=("exe","dll","sys","scr","cpl","ocx","efi")),
    S("Executables", "DOS ZM executable", b"ZM", "Rare DOS ZM executable header.", extensions=("exe",)),
    S("Executables", "Mach-O 32-bit", "FE ED FA CE", "Apple Mach-O 32-bit big-endian magic."),
    S("Executables", "Mach-O 32-bit — reversed", "CE FA ED FE", "Apple Mach-O 32-bit little-endian magic."),
    S("Executables", "Mach-O 64-bit", "FE ED FA CF", "Apple Mach-O 64-bit big-endian magic."),
    S("Executables", "Mach-O 64-bit — reversed", "CF FA ED FE", "Apple Mach-O 64-bit little-endian magic."),
    S("Executables", "Java class / Mach-O universal", "CA FE BA BE", "Magic shared by Java class files and some Mach-O universal binaries; extension/context may disambiguate.", extensions=("class",)),
    S("Executables", "WebAssembly binary", "00 61 73 6D", "WebAssembly binary module magic (\\0asm).", extensions=("wasm",)),
    S("Executables", "Android DEX bytecode", "64 65 78 0A 30 33 35 00", "Android Dalvik DEX version-035 header.", extensions=("dex",)),
    S("Executables", "Lua bytecode", "1B 4C 75 61", "Lua compiled-bytecode header.", extensions=("luac",)),
    S("Executables", "Preferred Executable Format", b"Joy!", "Preferred Executable Format header."),
    S("Executables", "U-Boot uImage", "27 05 19 56", "Das U-Boot legacy uImage header."),
    S("Executables", "Clang precompiled header", b"CPCH", "Clang precompiled-header magic.", extensions=("pch",)),
    S("Executables", "BSDIFF binary patch", b"BSDIFF40", "bsdiff binary-patch header."),

    # Databases / data / scientific
    S("Databases", "SQLite database", b"SQLite format 3\x00", "SQLite 3 database header.", extensions=("sqlite","sqlite3","db","sqlitedb")),
    S("Databases", "Microsoft Access 2007", b"\x00\x01\x00\x00Standard ACE DB", "Microsoft Access ACE database header.", extensions=("accdb",)),
    S("Databases", "Microsoft Access Jet", b"\x00\x01\x00\x00Standard Jet DB", "Microsoft Access Jet database header.", extensions=("mdb",)),
    S("Databases", "Microsoft Money", b"\x00\x01\x00\x00MSISAM Database", "Microsoft Money database header.", extensions=("mny",)),
    S("Databases", "DuckDB database", b"DUCK", "DuckDB database marker at offset 8.", offset=8, extensions=("duckdb","db")),
    S("Databases", "Windows Registry hive", b"regf", "Windows Registry hive header.", extensions=("dat","hiv")),
    S("Databases", "Windows custom database", b"sdbf", "Windows customized database marker at offset 8.", offset=8, extensions=("sdb",)),
    S("Databases", "Outlook PST", b"!BDN", "Microsoft Outlook Personal Storage Table header.", extensions=("pst",)),
    S("Data/Scientific", "HDF4", "0E 03 13 01", "Hierarchical Data Format version 4 header.", extensions=("hdf4","h4")),
    S("Data/Scientific", "HDF5", "89 48 44 46 0D 0A 1A 0A", "Hierarchical Data Format version 5 signature; may occur at allowed power-of-two offsets.", offsets=(0,512,1024,2048,4096,8192,16384,32768,65536), extensions=("hdf5","h5")),
    S("Data/Scientific", "FITS", b"SIMPLE  =", "Flexible Image Transport System primary header.", extensions=("fits","fit")),
    S("Data/Scientific", "DICOM", b"DICM", "DICOM medical-file marker at offset 128.", offset=128, extensions=("dcm",)),
    S("Data/Scientific", "NIfTI single-file", b"n+1\x00", "NIfTI single-file magic at offset 344.", offset=344, extensions=("nii",)),
    S("Data/Scientific", "NIfTI header", b"ni1\x00", "NIfTI paired header magic at offset 344.", offset=344, extensions=("hdr",)),
    S("Data/Scientific", "Apache Parquet", b"PAR1", "Apache Parquet columnar file header.", extensions=("parquet",)),
    S("Data/Scientific", "Apache ORC", b"ORC", "Apache ORC columnar file header.", extensions=("orc",)),
    S("Data/Scientific", "Apache Avro", "4F 62 6A 01", "Apache Avro object-container file header.", extensions=("avro",)),
    S("Data/Scientific", "RCFile", b"SEQ6", "RCFile columnar data header.", extensions=("rc",)),
    S("Data/Scientific", "GRIB / GRIB2", b"GRIB", "WMO GRIB-family gridded-data header.", extensions=("grib","grib2")),
    S("Data/Scientific", "ASTM E57 3D", b"ASTM-E57", "ASTM E57 3D data file.", extensions=("e57",)),
    S("Data/Scientific", "Tableau datasource", "20 02 01 62 A0 1E AB 07 02 00 00 00", "Tableau datasource file header.", extensions=("tde",)),
    S("Data/Scientific", "KDB database", "37 48 03 02 00 00 00 00 58 35 30 39 4B 45 59", "KDB file header.", extensions=("kdb",)),

    # Audio / video / containers
    S("Audio/Video", "Ogg container", b"OggS", "Ogg multimedia container header.", extensions=("ogg","oga","ogv")),
    S("Audio/Video", "FLAC audio", b"fLaC", "Free Lossless Audio Codec header.", extensions=("flac",)),
    S("Audio/Video", "WAVE audio", b"WAVE", "WAVE form marker at offset 8 inside a RIFF container.", offset=8, extensions=("wav",), guard=b"RIFF"),
    S("Audio/Video", "AVI video", b"AVI ", "AVI form marker at offset 8 inside a RIFF container.", offset=8, extensions=("avi",), guard=b"RIFF"),
    S("Audio/Video", "MP3 with ID3v2", b"ID3", "ID3v2 metadata header commonly found at the beginning of MP3 files.", extensions=("mp3",)),
    S("Audio/Video", "MP3 frame sync FF FB", "FF FB", "Common MPEG Layer III frame-sync bytes.", extensions=("mp3",), auto_detect=False),
    S("Audio/Video", "MP3 frame sync FF F3", "FF F3", "Common MPEG Layer III frame-sync bytes.", extensions=("mp3",), auto_detect=False),
    S("Audio/Video", "MP3 frame sync FF F2", "FF F2", "Common MPEG Layer III frame-sync bytes.", extensions=("mp3",), auto_detect=False),
    S("Audio/Video", "MIDI file", b"MThd", "Standard MIDI file header.", extensions=("mid","midi")),
    S("Audio/Video", "Matroska / WebM", "1A 45 DF A3", "EBML header used by Matroska and WebM containers.", extensions=("mkv","mka","mks","mk3d","webm")),
    S("Audio/Video", "ISO Base Media / MP4 family", b"ftyp", "ISO Base Media File Format ftyp box marker.", offset=4, extensions=("mp4","m4v","mov","heic","heif","3gp","3g2")),
    S("Audio/Video", "MP4 — isom brand", b"ftypisom", "ISO Base Media / MPEG-4 isom brand.", offset=4, extensions=("mp4",)),
    S("Audio/Video", "MP4 — MSNV brand", b"ftypMSNV", "MPEG-4 MSNV brand.", offset=4, extensions=("mp4",)),
    S("Audio/Video", "3GPP media", b"ftyp3g", "3GPP/3GPP2 ISO-base-media brand prefix.", offset=4, extensions=("3gp","3g2")),
    S("Audio/Video", "AIFF audio", b"AIFF", "AIFF form marker at offset 8 inside an IFF FORM container.", offset=8, extensions=("aiff","aif","aifc","snd"), guard=b"FORM"),
    S("Audio/Video", "ASF / WMA / WMV", "30 26 B2 75 8E 66 CF 11 A6 D9 00 AA 00 62 CE 6C", "Advanced Systems Format header.", extensions=("asf","wma","wmv")),
    S("Audio/Video", "Flash Video", b"FLV", "Flash Video header.", extensions=("flv",)),
    S("Audio/Video", "MPEG Program Stream", "00 00 01 BA", "MPEG program-stream pack header.", extensions=("m2p","vob","mpg","mpeg")),
    S("Audio/Video", "MPEG video sequence", "00 00 01 B3", "MPEG-1/2 video sequence header.", extensions=("mpg","mpeg")),
    S("Audio/Video", "AMR audio", b"#!AMR", "Adaptive Multi-Rate audio header.", extensions=("amr",)),
    S("Audio/Video", "SILK audio", b"#!SILK\n", "Skype SILK audio header.", extensions=("sil",)),
    S("Audio/Video", "Creative Voice", b"Creative Voice File\x1a\x1a\x00", "Creative Voice audio-file header.", extensions=("voc",)),
    S("Audio/Video", "AU/SND audio", b".snd", "Sun/NeXT AU audio header.", extensions=("au","snd")),
    S("Audio/Video", "Digital Speech Standard v2", "02 64 73 73", "Digital Speech Standard version 2 header.", extensions=("dss",)),
    S("Audio/Video", "Digital Speech Standard v3", "03 64 73 73", "Digital Speech Standard version 3 header.", extensions=("dss",)),
    S("Audio/Video", "M3U playlist", b"#EXTM3U", "Extended M3U playlist header.", extensions=("m3u","m3u8")),
    S("Containers", "RIFF container", b"RIFF", "Resource Interchange File Format container header."),
    S("Containers", "IFF FORM container", b"FORM", "Interchange File Format FORM container header.", extensions=("iff",)),
    S("Containers", "IFF ILBM image", b"ILBM", "IFF Interleaved Bitmap form marker at offset 8.", offset=8, extensions=("ilbm","lbm","iff"), guard=b"FORM"),
    S("Containers", "IFF 8SVX audio", b"8SVX", "IFF 8-bit sampled-voice form marker at offset 8.", offset=8, extensions=("8svx","8sv","svx","snd","iff"), guard=b"FORM"),
    S("Containers", "RIFF animated cursor", b"ACON", "Animated-cursor form marker at offset 8 inside RIFF.", offset=8, extensions=("ani",), guard=b"RIFF"),
    S("Containers", "RIFF CDDA", b"CDDA", "CD Audio form marker at offset 8 inside RIFF.", offset=8, extensions=("cda",), guard=b"RIFF"),
    S("Containers", "RIFF QLCM", b"QLCM", "Qualcomm PureVoice form marker at offset 8 inside RIFF.", offset=8, extensions=("qcp",), guard=b"RIFF"),
    S("Containers", "Binary glTF", b"glTF", "Binary glTF (GLB) header.", extensions=("glb",)),
    S("Containers", "Blender file", b"BLENDER", "Blender native file header.", extensions=("blend",)),
    S("Containers", "Google Draco", b"DRACO", "Google Draco compressed 3D model header.", extensions=("drc",)),
    S("Containers", "Material Exchange Format", "06 0E 2B 34 02 05 01 01 0D 01 02 01 01 02", "MXF universal-label prefix; MXF may have a variable run-in before this marker.", extensions=("mxf",), auto_detect=False),

    # Fonts
    S("Fonts", "TrueType font", "00 01 00 00", "TrueType sfnt version marker.", extensions=("ttf","tte","dfont")),
    S("Fonts", "OpenType font", b"OTTO", "OpenType font with CFF outlines.", extensions=("otf",)),
    S("Fonts", "WOFF font", b"wOFF", "Web Open Font Format 1 header.", extensions=("woff",)),
    S("Fonts", "WOFF2 font", b"wOF2", "Web Open Font Format 2 header.", extensions=("woff2",)),

    # Network captures
    S("Network", "PCAP — little endian", "D4 C3 B2 A1", "libpcap capture file, little-endian microsecond-resolution magic.", extensions=("pcap",)),
    S("Network", "PCAP — big endian", "A1 B2 C3 D4", "libpcap capture file, big-endian microsecond-resolution magic.", extensions=("pcap",)),
    S("Network", "PCAP nanosecond — little endian", "4D 3C B2 A1", "libpcap capture file, little-endian nanosecond-resolution magic.", extensions=("pcap",)),
    S("Network", "PCAP nanosecond — big endian", "A1 B2 3C 4D", "libpcap capture file, big-endian nanosecond-resolution magic.", extensions=("pcap",)),
    S("Network", "PCAPNG capture", "0A 0D 0D 0A", "pcapng section-header block magic.", extensions=("pcapng",)),
    S("Network", "SmartSniff packets", b"SMSNF200", "SmartSniff packet-capture file header.", extensions=("ssp",)),

    # Disk images / virtualization / forensic containers
    S("Disk/Virtualization", "ISO 9660 image", b"CD001", "ISO 9660 volume descriptor identifier; common primary descriptor offsets are checked.", offsets=(0x8001,0x8801,0x9001), extensions=("iso",)),
    S("Disk/Virtualization", "VMware VMDK", b"KDM", "VMDK binary disk header.", extensions=("vmdk",)),
    S("Disk/Virtualization", "VMware VMDK descriptor", b"# Disk Descriptor", "VMware split-disk text descriptor.", extensions=("vmdk",)),
    S("Disk/Virtualization", "Apple DMG", b"koly", "Apple Disk Image trailer marker located 512 bytes before EOF.", offset=-512, extensions=("dmg",)),
    S("Disk/Virtualization", "Roxio Toast image", "45 52 02 00 00 00", "Roxio Toast disk-image header.", extensions=("toast",)),
    S("Disk/Virtualization", "VirtualBox VDI", b"<<< Oracle VM VirtualBox Disk Image >>>", "VirtualBox virtual-disk image header.", extensions=("vdi",)),
    S("Disk/Virtualization", "Virtual PC VHD", b"conectix", "Virtual Hard Disk footer/header marker.", extensions=("vhd",)),
    S("Disk/Virtualization", "VHDX image", b"vhdxfile", "Windows VHDX virtual-disk header.", extensions=("vhdx",)),
    S("Disk/Virtualization", "ISZ image", b"IsZ!", "Compressed ISO image header.", extensions=("isz",)),
    S("Disk/Virtualization", "DAA image", b"DAA", "PowerISO Direct Access Archive header.", extensions=("daa",)),
    S("Disk/Virtualization", "QCOW image", b"QFI", "QCOW virtual-disk header.", extensions=("qcow","qcow2")),
    S("Disk/Virtualization", "Advanced Forensics Format", b"AFF", "Advanced Forensics Format header.", extensions=("aff",)),
    S("Disk/Virtualization", "EnCase EWF v1", b"EVF", "EnCase Expert Witness Format version 1 header.", extensions=("e01",)),
    S("Disk/Virtualization", "EnCase EWF v2", b"EVF2", "EnCase Expert Witness Format version 2 header.", extensions=("ex01",)),

    # System / logs / games / other
    S("System", "Windows EVT log", b"LfLe", "Legacy Windows Event Viewer log.", extensions=("evt",)),
    S("System", "Windows EVTX log", b"ElfFile", "Windows Event Log XML-format file.", extensions=("evtx",)),
    S("System", "systemd journal", b"LPKSHHRH", "systemd-journald log-file header.", extensions=("journal",)),
    S("System", "CrowdStrike channel file", "AA AA AA AA", "CrowdStrike channel-file header.", extensions=("sys",), auto_detect=False),
    S("Games", "Doom IWAD", b"IWAD", "Doom internal WAD resource-file header.", extensions=("wad",)),
    S("Games", "Valve VPK", "34 12 AA 55", "Valve/Source Engine VPK archive header.", extensions=("vpk",)),
    S("Games", "Capcom RE Engine archive", b"KPKA", "Capcom RE Engine game-data archive.", extensions=("pak",)),
    S("Games", "Capcom MT Framework archive", b"ARC", "Capcom MT Framework game-data archive.", extensions=("arc",)),
    S("Games", "NES ROM", "4E 45 53 1A", "iNES/NES ROM header.", extensions=("nes",)),
    S("Games", "Unreal UCAS", "8C 0A 00", "Unreal Engine compressed asset-storage file.", extensions=("ucas",)),
    S("Games", "Unreal UTOC", b"-==--==--==--==-", "Unreal Engine table-of-contents file.", extensions=("utoc",)),
    S("Other", "Telegram Desktop file", b"TDF$", "Telegram Desktop data file.", extensions=("tdf$",)),
    S("Other", "Telegram encrypted file", b"TDEF", "Telegram Desktop encrypted data file.", extensions=("tdef",)),
    S("Other", "macOS binary property list", b"bplist", "Binary Apple property-list header.", extensions=("plist",)),
    S("Other", "macOS alias", b"book\x00\x00\x00\x00mark\x00\x00\x00\x00", "macOS Finder alias file header.", extensions=("alias",)),
    S("Other", "SAP Power Monitor data", b"pwrdata", "SAP Power Monitor data-file header.", extensions=("pwrdata",)),
    S("Other", "Ion binary encoding", "E0 01 00 EA", "Amazon Ion binary serialization header."),
)

ASCII_CONTROLS = (
    (0x00, "NUL", "Null"), (0x07, "BEL", "Bell"), (0x08, "BS", "Backspace"),
    (0x09, "TAB", "Horizontal tab"), (0x0A, "LF", "Line feed"), (0x0B, "VT", "Vertical tab"),
    (0x0C, "FF", "Form feed"), (0x0D, "CR", "Carriage return"), (0x1B, "ESC", "Escape"),
    (0x20, "SP", "Space"), (0x7F, "DEL", "Delete"),
)


def _matches(data: bytes, sig: Signature) -> bool:
    return len(data) >= len(sig.pattern) and data[:len(sig.pattern)] == sig.pattern


def _specificity(sig: Signature) -> int:
    return len(sig.pattern) + len(sig.guard)


def likely_signatures(prefix: bytes) -> list[Signature]:
    """Return all signatures that can be established from an already-read prefix."""
    matches: list[Signature] = []
    for sig in SIGNATURES:
        for off in sig.candidate_offsets():
            if off < 0:
                continue
            end = off + len(sig.pattern)
            if end > len(prefix) or prefix[off:end] != sig.pattern:
                continue
            if sig.guard:
                gend = sig.guard_offset + len(sig.guard)
                if gend > len(prefix) or prefix[sig.guard_offset:gend] != sig.guard:
                    continue
            matches.append(sig)
            break
    return sorted(matches, key=lambda s: (_specificity(s), len(s.pattern), s.name), reverse=True)


def likely_signature(prefix: bytes) -> Signature | None:
    matches = likely_signatures(prefix)
    return matches[0] if matches else None


def _extension_for(path: object) -> str:
    try:
        return Path(path).suffix.lower().lstrip('.')
    except Exception:
        return ""


def identify_source(source) -> Signature | None:
    """Identify a ByteSource-like object using bounded targeted reads.

    Unlike likely_signature(), this can recognise fixed non-zero offsets and the
    DMG EOF-512 trailer without loading the file.  Only conservative auto_detect
    entries participate; weaker signatures remain available in the Byte Library.
    """
    ext = _extension_for(getattr(source, "path", ""))
    size = int(getattr(source, "size", 0))

    # Group candidate reads by physical offset so opening a file does not issue
    # one pread per signature. Most knowledge lives at offset 0, so this usually
    # becomes one small header read plus a few targeted fixed-offset reads.
    read_sizes: dict[int, int] = {}
    for sig in SIGNATURES:
        if not sig.auto_detect:
            continue
        for nominal in sig.candidate_offsets():
            off = size + nominal if nominal < 0 else nominal
            if 0 <= off < size:
                read_sizes[off] = max(read_sizes.get(off, 0), len(sig.pattern))
        if sig.guard:
            goff = size + sig.guard_offset if sig.guard_offset < 0 else sig.guard_offset
            if 0 <= goff < size:
                read_sizes[goff] = max(read_sizes.get(goff, 0), len(sig.guard))
    cache = {off: source.read(off, min(length, max(0, size - off))) for off, length in read_sizes.items()}

    found: list[tuple[Signature, int]] = []
    for sig in SIGNATURES:
        if not sig.auto_detect:
            continue
        for nominal in sig.candidate_offsets():
            off = size + nominal if nominal < 0 else nominal
            if off < 0 or off + len(sig.pattern) > size:
                continue
            if cache.get(off, b"")[:len(sig.pattern)] != sig.pattern:
                continue
            if sig.guard:
                goff = size + sig.guard_offset if sig.guard_offset < 0 else sig.guard_offset
                if goff < 0 or goff + len(sig.guard) > size or cache.get(goff, b"")[:len(sig.guard)] != sig.guard:
                    continue
            found.append((sig, nominal))
            break
    if not found:
        return None
    # Specific magic wins. Extension is a tie-breaker for container families that
    # deliberately share the same bytes (ZIP-based formats, CAFEBABE ambiguity).
    return max((s for s, _ in found), key=lambda s: (_specificity(s), 1 if ext and ext in s.extensions else 0, len(s.pattern), s.name))


def offset_text(sig: Signature) -> str:
    offsets = sig.candidate_offsets()
    parts=[]
    for off in offsets:
        if off < 0:
            parts.append(f"EOF{off:+d}".replace("+-", "-"))
        else:
            parts.append(f"0x{off:X}" if off >= 10 else str(off))
    return ", ".join(parts)


def extensions_text(sig: Signature) -> str:
    return ", ".join(f".{e}" for e in sig.extensions) if sig.extensions else "Not specified"


def library_rows() -> list[tuple[str, str, bytes, str, str, str, bool]]:
    rows = [(s.category, s.name, s.pattern, s.description, offset_text(s), extensions_text(s), s.auto_detect) for s in SIGNATURES]
    rows += [("ASCII", f"0x{value:02X} {abbr}", bytes([value]), desc, "Any", "Not applicable", False)
             for value, abbr, desc in ASCII_CONTROLS]
    return rows
