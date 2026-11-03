<p align="center">
  <a href="https://github.com/brunonlinespace/beespector-lite">
    <img
      src="beespector_lite/assets/icons/beespector.png"
      alt="Beespector Lite"
      width="256"
    >
  </a>
</p>

# Beespector Lite

**Friendly. Fast. Focused.**

Beespector Lite is the streamlined, strictly read-only edition of Beespector. It keeps the full single-file binary/hex inspection, search, analysis, file-signature, metadata, bookmark, and export toolset while deliberately omitting every multi-file comparison and difference workflow.

Current release: **0.0.4**

Repository: <https://github.com/brunonlinespace/beespector-lite>

## What Beespector Lite is

Beespector Lite is designed for people who want Beespector's file-inspection tools in a smaller single-file application. A regular file is opened directly through the read-only byte engine and displayed as offsets, hexadecimal bytes, and optional ASCII without introducing an editing layer, private file format, workspace database, or comparison relationship.

Lite is intentionally not a reduced-safety edition. It keeps the same read-only source boundary and the same core inspection engines while removing mainline Beespector's Compare pane, Primary/Compared roles, difference scanning, comparison summaries, and multi-pane command architecture.

## Highlights

- Strictly **read-only single-file inspection** through an `O_RDONLY` byte source.
- Virtualized **Offset + Hex + ASCII** file view.
- 8 / 16 / 32-byte presets plus custom **1–64 bytes per row**.
- Hexadecimal, Decimal, and **Hex + Decimal** offset displays.
- Optional ASCII and hexadecimal column identifiers.
- Dark / Light canvas modes, configurable display font, font size, and text-colour modes.
- Byte/Text **Find**, Find Next/Previous, Find All, and Go to Offset.
- **Selection Inspector** with integer and endian-aware interpretations.
- Selected-range **SHA-256, MD5, and CRC32** checksums.
- **Strings Finder**, Shannon entropy inspection, and repeated-byte-run analysis.
- Privacy-preserving **Bookmarks** without persisted inspected source paths.
- **Byte Library** with 257 curated file-signature/reference entries and bounded source-aware identification.
- Read-only **File Information / Metadata** with filesystem, embedded-format, and integrity views.
- Copy Hex / Compact Hex / Escaped Bytes / ASCII / Offset / Offset + Bytes.
- **Export Selection** to a separate destination only.
- Permanent **Main Toolbar** plus independently optional Shortcut Toolbar and lower Find Bar.
- Configurable file drag-and-drop behavior for the active window or a new Beespector Lite window.
- Searchable **Keyboard Shortcuts** reference, bundled documentation, GitHub and issue links.
- No comparison, difference scanning, merge, or write-back path.

## Interface

### Main Toolbar

Beespector Lite keeps one permanent **Main Toolbar** above the viewer with all application menus in a single row:

**File · Edit · Inspect · View · Help**

The Main Toolbar is the primary command surface and is intentionally always visible. It cannot be hidden through View settings or toolbar context controls.

Lite does not use mainline Beespector's native AppMenu / Global Toolbar / per-pane Action Toolbar architecture. Its command layout remains deliberately compact and single-file.

### Shortcut Toolbar

The optional **Shortcut Toolbar** sits immediately below the Main Toolbar and contains user-selected commands.

Use **View → Toolbars → Add More Shortcuts…** to choose commands for that row. **Reset Shortcut Toolbar** returns it to an empty custom set. Shortcut Toolbar visibility is persistent and independent from the Main Toolbar.

### Find Bar

The **Find Bar** remains independent and sits below the Hex/ASCII viewer. It can be shown or hidden separately from the Shortcut Toolbar.

Find supports Text / Hex search, next/previous navigation, and Find All. `Enter` performs Find Next and `Shift+Enter` performs Find Previous.

The compact path header displays the end of the active path while the complete path remains available on hover.

## Inspection

Beespector Lite retains the single-file inspection toolset from mainline Beespector:

- Offset, Hex, and optional ASCII display;
- configurable bytes per row;
- optional column identifiers;
- Hexadecimal, Decimal, or Hex + Decimal offsets;
- selection and copy operations;
- configurable display font and font size;
- Dark / Light canvas presentation;
- text-colour modes;
- Go to Offset;
- Selection Inspector;
- selected-range checksums;
- Strings Finder;
- entropy inspection;
- repeated-byte runs;
- bookmarks;
- Export Selection.

The viewer remains an inspector rather than an editor. There are no source-byte insertion, deletion, overwrite, or truncation commands.

## Byte Library and file knowledge

The Byte Library contains **257 curated signature/reference entries** and combines reference material with conservative automatic identification.

Recognition uses bounded targeted reads at known signature locations, including supported non-zero offsets and selected alternate positions. Shared-container formats can use extension-aware refinement, while weak or ambiguous signatures can remain useful Library references without participating in automatic detection.

Library details expose information such as signature bytes, signature offset, known extensions, description, and automatic-detection status.

Byte Library can be placed as:

- **Floating**;
- **Sidebar Left**;
- **Sidebar Right**.

Its selected placement is remembered independently from visibility. Docked width is constrained to a compact 240–420 px range, the docked Library has its own close control, and the internal list/details divider remains user-adjustable.

## File Information / Metadata

**File Information / Metadata…** (`Alt+Return`) provides read-only file knowledge without requiring the format to be editable or even recognised.

The inspector covers:

- Summary;
- filesystem information;
- detected signature and format knowledge;
- Embedded Metadata;
- Integrity.

Bounded embedded readers cover formats including PNG, JPEG, GIF, ZIP-family containers, PDF, ELF, Windows PE, SQLite, and RIFF/WAVE. Unknown files remain valid inspection targets and still receive universal filesystem and signature information where available.

## Drag and drop

**View → File Drag and Drop** provides two ordinary behaviors:

- **Opens on Active Window**; or
- **Opens on New Window**.

Holding **Shift** uses the opposite Active/New destination for that drop.

Ctrl has no special drop behavior in Lite because the application has no comparison relationship.

## Read-only guarantees and privacy

Beespector Lite is an inspector, not a file editor.

- Only regular source files are accepted.
- Sources are opened through `ByteSource` using `O_RDONLY` and there is no source-write API.
- There is no Save, Save As, overwrite, insert-byte, delete-byte, truncate, raw-device, process-memory, or comparison path.
- Export Selection writes to a separate destination and does not modify the inspected source.
- Metadata inspection is read-only.
- Open Recent is deliberately absent.
- Bookmarks are keyed from content fingerprints and do not persist inspected source paths.
- External-change detection is advisory; Beespector Lite does not claim to stop another process from changing a file while it is open.

## Useful keyboard shortcuts

| Command | Shortcut |
| --- | --- |
| Open | `Ctrl+O` |
| Reload | `F5` |
| File Information / Metadata | `Alt+Return` |
| Find | `Ctrl+F` |
| Find Next | `Enter` |
| Find Previous | `Shift+Enter` |
| Find All Current Search | `Ctrl+Shift+F` |
| Go to Offset | `Ctrl+G` |
| Selection Inspector | `Ctrl+I` |
| Entropy | `Ctrl+E` |
| Strings Finder | `Ctrl+Alt+S` |
| Add Bookmark | `Ctrl+B` |
| Manage Bookmarks | `Ctrl+Shift+B` |
| Byte Library | `Ctrl+L` |
| 8 / 16 / 32 Bytes Per Row | `Ctrl+1` / `Ctrl+2` / `Ctrl+3` |
| Show Column Identifiers | `Ctrl+Alt+I` |
| Keyboard Shortcuts | `Ctrl+Shift+/` |

The searchable **Help → Keyboard Shortcuts** dialog is the authoritative in-application reference for the complete current shortcut set.

## Running from source

Beespector Lite uses the common source-portable layout:

```text
main.py
suite-pythoine-component.json
beespector_lite/
```

The current runtime requirement is Python 3 with PyQt6 6.7 or later, below Qt/PyQt 7.

From the extracted source root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r beespector_lite/requirements.txt
python3 main.py
```

`main.py` is the canonical source-portable entrypoint.

## Building the AppImage

The Fedora AppImage builder is:

```bash
bash beespector_lite/packaging/fedora/build-appimage.sh
```

The current builder is validated for **Fedora 43/44** on native **x86_64** and **aarch64**. It is intentionally non-privileged, creates an isolated build environment, runs Lite QA, freezes the application with PyInstaller, assembles the AppDir, validates the fixed Beespector Lite identity, smoke-tests the packaged runtime, and emits release provenance alongside the AppImage.

Expected outputs are written beneath `beespector_lite/dist/` and include:

```text
Beespector-Lite-0.0.4-<arch>.AppImage
Beespector-Lite-0.0.4-<arch>.AppImage.sha256
Beespector-Lite-0.0.4-<arch>.build-info.txt
Beespector-Lite-0.0.4-<arch>.build-python-lock.txt
```

Do not normally run the builder with `sudo` or as root.

## Validation

Run the source QA and release gate with:

```bash
bash beespector_lite/qa/run-qa.sh
```

The retained QA covers fixed Lite identity, read-only source contracts, viewer and analysis behavior, menus and toolbar architecture, metadata and signatures, settings, bundled assets, AppImage metadata, the deliberate absence of comparison functionality, and source-manifest integrity.

## Configuration

Beespector Lite stores per-user preferences outside inspected files.

Linux:

```text
~/.config/brunonlinespace/beespector-lite/beespector-lite.json
```

Windows:

```text
%APPDATA%\brunonlinespace\beespector-lite\beespector-lite.json
```

Bookmarks are stored separately beside the application preferences and use content fingerprints rather than persisted source paths.

## Scope

Beespector Lite is a **single-file read-only binary, hexadecimal, and metadata inspector**. It deliberately excludes mainline Beespector's comparison relationship and does not become a hex editor, binary patcher, raw-device editor, process-memory editor, workspace manager, or file-merging application.

Its goal is to keep the core Beespector inspection experience compact while preserving the same clear read-only boundary around the source file.

## License

Beespector Lite is licensed under the **GNU General Public License v3.0 or later**.

See `beespector_lite/LICENSE` for the complete license text.

## Links

- Beespector Lite: <https://github.com/brunonlinespace/beespector-lite>
- Issues: <https://github.com/brunonlinespace/beespector-lite/issues>
- GitHub profile: <https://github.com/brunonlinespace/>

Copyright © 2026 Bruno Machado.
