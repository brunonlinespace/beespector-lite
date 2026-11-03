# Beespector Lite 0.0.2-r1 — Release Audit

## Baseline

This release was built directly from the user-supplied archive:

- `Beespector-Lite-0.0.1-exp5-r1-source.zip`
- SHA-256: `c07a9e58d2b2d475a2936d36022b817b75e481134cbb2593476c985ea1dca3a3`

It does **not** use the previously issued Lite exp6 tree as its implementation base.

## Scope

exp7 ports only the richer Byte Library / file-identification knowledge to the supplied exp5-r1 codebase and advances the application version to `0.0.2-r1`.

Preserved from the supplied exp5-r1 source:

- permanent File / Edit / Inspect / View / Help Main Toolbar;
- separate Shortcut Toolbar;
- lower Find Bar;
- File Drag and Drop terminology and Active/New Window behaviour;
- Ctrl+E Entropy shortcut;
- compact/stateful Byte Library sidebar geometry;
- all comparison-free Lite behaviour;
- existing Lite application artwork and packaging identity.

## Rich file knowledge

- Signature/reference catalogue expanded from 58 to 257 entries.
- Entries include categories for images, archives, documents, executables, audio/video, fonts, network formats, packages, data/scientific files, disk/virtualization formats, encodings and keys/certificates.
- Source-aware identification uses bounded targeted reads instead of assuming every signature is at offset 0.
- Supports fixed non-zero offsets and selected EOF-relative signatures.
- Weak/ambiguous signatures may remain visible in Byte Library while `auto_detect=False` prevents them from automatically identifying arbitrary files.
- Shared-container formats can use extension-aware tie-breaking where signature bytes are intentionally identical.
- Byte Library details now expose Offset, Known extensions and Detection status.
- File Information / Metadata now exposes Signature offset, Signature bytes, Known extensions and Signature knowledge.
- Status-bar likely-type identification now uses the same source-aware detector.

## Read-only / bounded-resource contract

- Inspected file access remains through `ByteSource` and `O_RDONLY`.
- No source write API was added.
- Detection uses bounded positional reads rather than whole-file loading.
- Comparison remains absent from Lite.

## Artwork

The Lite master application artwork is unchanged:

`dc309e4b1f4b5e0c37ccaf4008998b397b50ea51a929529f103e0f39a9f8161a`

## QA

The working tree passed:

- 53/53 Python unit tests;
- release checker;
- Python AST parse of 26 source files;
- Bash syntax checks for portable launcher, AppRun and Fedora AppImage builder;
- AppStream XML parse;
- rich catalogue count check (257 entries);
- non-zero-offset recognition tests (including DICOM and ISO 9660);
- reference-only weak-signature test;
- extension-aware ZIP-family refinement test;
- metadata signature-offset/extensions test.

The final ZIP is separately re-extracted and re-tested before release.
