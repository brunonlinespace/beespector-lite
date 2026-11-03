# Beespector Lite 0.0.4 — Release Notes

Beespector Lite 0.0.4 is a narrowly scoped AppImage-builder reliability release built directly from 0.0.3. Application inspection, UI, search, shortcuts, toolbar presentation, Byte Library behavior, and file workflow behavior are unchanged.

The Fedora AppImage builder now resolves the AppImage Type-2 runtime explicitly before packaging, using the builder's guarded HTTPS download path, caches it alongside appimagetool, validates it as an ELF file, supports optional SHA-256 verification, records its resolved hash in build information, and passes it to appimagetool with `--runtime-file`. This removes appimagetool's hidden last-step runtime download that could fail after an otherwise successful build.

The repository-root `README.md` remains locked public-facing content and is changed only for the 0.0.3 → 0.0.4 version references.
