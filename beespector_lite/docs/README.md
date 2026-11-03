# Beespector Lite 0.0.4

Beespector Lite is the streamlined, strictly read-only edition of Beespector. It retains the full single-file inspection toolset while deliberately omitting every multi-file comparison/difference feature.

## Core inspection

- Offset + hexadecimal + ASCII file view.
- 8 / 16 / 32 byte presets and Custom 1–64 bytes per row.
- Optional Offset, ASCII and hexadecimal column identifiers.
- Hexadecimal, Decimal, or Hex + Decimal offset display.
- Dark / Light canvas and text-colour modes.
- Configurable display font and font size.
- Byte/text Find, Find Next/Previous and Find All.
- Go to Offset.
- Selection Inspector with integer/endian interpretations.
- Selected-range SHA-256, MD5 and CRC32.
- Strings Finder.
- Shannon entropy inspection.
- Repeated Byte Runs.
- Content-fingerprinted bookmarks without storing inspected paths.
- Byte Library signatures with Find / Find All.
- File Information / Metadata with filesystem, embedded-format and integrity views.
- Copy Hex / Compact Hex / Escaped Bytes / ASCII / Offset / Offset + Bytes.
- Export Selection to a new destination only.

## exp5 interface

exp5 uses one fixed menu row plus two independent auxiliary surfaces:

- permanent **Main Toolbar** above the viewer with **File / Edit / Inspect / View / Help** menus;
- Main Toolbar is always visible and cannot be hidden;
- optional **Shortcut Toolbar** immediately below it for user-selected commands;
- **Add More Shortcuts…** selects commands for the Shortcut Toolbar;
- Shortcut Toolbar can be shown/hidden from View → Toolbars or the toolbar context menu;
- fixed Find Bar remains **below** the Hex/ASCII view and can also be shown/hidden;
- no application QMenuBar/global-menu export in this experimental line;
- compact file path shown as `…/parent/file`, with the full path on hover;
- persistent Status Bar visibility with corrected check-state synchronisation.

The custom mainline Beespector toolbar icon family is **not included**. Beespector Lite retains its existing application icon family unchanged and uses text controls/system Find icons.

## Byte Library and file knowledge

- 257 curated file-signature/reference entries derived from the Wikipedia List of file signatures and conservative supplemental classification.
- File recognition supports bounded targeted reads at real fixed offsets and selected EOF-relative locations instead of assuming all magic bytes begin at offset 0.
- Shared-container formats can use extension-aware refinement where the signature bytes alone are intentionally identical.
- Ambiguous/weak signatures can remain useful Library references without participating in automatic identification.
- Library details show signature offset, known extensions and whether an entry participates in automatic detection.
- File Information / Metadata reports matched signature offset, bytes, known extensions and signature knowledge.
- One checkable Byte Library visibility action.
- Floating / Sidebar Left / Sidebar Right are placement-and-toggle controls.
- Docked sidebar width is constrained to 240–420 px, defaulting to 320 px.
- Docked Library has its own close button.
- Signature list is above the details panel.
- The top/bottom Library divider is user-adjustable.
- Closing the Library remembers its selected placement.

## Key shortcuts

- `Alt+Return` — File Information / Metadata.
- `Ctrl+E` — Entropy.
- `Ctrl+F` — focus Find bar.
- `Enter` — Find Next.
- `Shift+Enter` — Find Previous.
- `Ctrl+1` / `Ctrl+2` / `Ctrl+3` — 8 / 16 / 32 bytes per row.
- `Ctrl+Alt+I` — Show Column Identifiers.
- `Ctrl+L` — Byte Library.

## Drag and drop

View → **File Drag and Drop** provides:

- **Opens on Active Window**; or
- **Opens on New Window**.

Holding **Shift** uses the opposite Active/New destination. Ctrl has no special drop behaviour in Lite.

## Read-only guarantees

Beespector Lite opens regular source files through `ByteSource` with `O_RDONLY`. It has no source-file Save, Save As, overwrite, insert/delete-byte, truncate, raw-device, process-memory, or comparison path.

Export Selection is a one-way extraction to a new destination and never writes back into the inspected source.

## Identity

- Product: `Beespector Lite`
- Component ID: `beespector-lite`
- Python package: `beespector_lite`
- Executable: `beespector-lite`
- AppStream ID: `io.github.brunonlinespace.beespector-lite`
- Developer: `brunonlinespace`

The portable source root contains only `main.py` and `beespector_lite/`.
