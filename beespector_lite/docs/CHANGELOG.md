# Changelog

## 0.0.4 — 2026-11-03

- Fixed AppImage packaging reliability by resolving and caching the Type-2 runtime explicitly before appimagetool runs.
- Validate the runtime as ELF, optionally verify `APPIMAGE_RUNTIME_SHA256`, and record its resolved SHA-256 in build information.
- Pass the runtime explicitly with `--runtime-file`, preventing appimagetool from performing a hidden final network fetch.
- Application behavior and UI are unchanged from 0.0.3.
- Root `README.md` content remains locked apart from release-version references.

## 0.0.3 — 2026-11-02

- Added the approved public GitHub `README.md` at repository root.
- Advanced release identity and packaging metadata to 0.0.3.
- No application UI, inspection, search, comparison, shortcut, toolbar/tab, or workflow behavior changes.


## 0.0.2-r1 — 2026-09-24
- Packaging-only hotfix for Suite-managed paths containing spaces.
- Quotes the build-environment Python executable during build-info generation.
- Makes the finished-AppImage version smoke-test failure explicitly fatal.
- No application, inspection, UI, routing, or workflow behavior changes.


## 0.0.2 — 2026-09-24
- AppImage/portable packaging normalization for Suite Pythoine.
- Version identity synchronized to 0.0.2.
- About slogan updated to “Friendly. Fast. Focused.”


## 0.0.1-exp7 — 2026-08-23

- Rebased directly from the user-supplied 0.0.1-exp5-r1 source tree.
- Expanded Byte Library/file knowledge from 58 to 257 curated signatures/reference entries.
- Added bounded source-aware detection at real fixed offsets and selected EOF-relative offsets.
- Added conservative automatic-detection flags so weak/ambiguous signatures can remain reference-only.
- Added offset, known-extension and detection-status information to Byte Library details.
- Added richer signature offset/bytes/extensions/knowledge fields to File Information / Metadata.
- Preserved the exp5-r1 UI, shortcuts, branding and strict comparison-free/read-only scope.

### exp5-r1 source hotfix — 2026-08-20

- Relabelled View → File Drag and Drop.
- Assigned Ctrl+E to Entropy….
- Application version remains 0.0.1-exp5.


## 0.0.1-exp5 — 2026-08-20

- Consolidated File / Edit / Inspect / View / Help into one permanent Main Toolbar above the viewer.
- Split user-selected command buttons into a dedicated independently hideable Shortcut Toolbar.
- Renamed shortcut configuration to Add More Shortcuts… and made the chooser cover File, Edit, Inspect, Find, View and Help commands.
- Main Toolbar can no longer be hidden; Shortcut Toolbar and Find Bar remain independently hideable.
- Kept Find Bar below the viewer.
- Renamed View → Behaviour to View → File Drag and Drop, with Opens on Active Window / Opens on New Window choices.
- Read-only inspection, comparison absence, Byte Library, branding and packaging remain unchanged.

## 0.0.1-exp4 — 2026-08-20

- Rebased intentionally from 0.0.1-exp2 rather than the exp3 UI rollback.
- Replaced the File / Edit / Inspect tabbed Action Toolbar with classic raised menu buttons matching View / Help.
- Preserved the former tab action order and separators inside conventional instant-popup menus.
- Removed Action-tab wheel/touch navigation and Ctrl+Tab / Ctrl+Shift+Tab Action-tab shortcuts because there are no longer tabs.
- Retained exp2's fixed lower Find bar, compact path, Global Toolbar, global shortcut customization, improved Byte Library, revised shortcuts and read-only inspection features.
- Comparison remains absent and Lite artwork remains unchanged.

## 0.0.1-exp3 — 2026-08-20

- Restored the original Lite exp1 UI architecture as an experimental rollback.
- exp4 does not use this release as its implementation base.

## 0.0.1-exp2 — 2026-08-19

- Experimental port of applicable mainline Beespector UI innovations into Lite.
- Added the single-file Action Toolbar, lower Find bar, Global Toolbar, stateful Byte Library and associated shortcut refinements.

## 0.0.1-exp1 — 2026-08-19

- First Beespector Lite experimental release.
- Established independent `beespector-lite` / `beespector_lite` application identity.
- Removed the complete multi-file comparison/difference subsystem from the Lite code, UI, preferences, packaging QA and tests.
- Retained Beespector's read-only inspection engine and metadata/analysis tools.
- Retained Active/New Window drag/drop defaults with Shift inversion.
