# Security and read-only design

Beespector Lite is an inspector, not a file editor.

Source files are accepted only as regular files and are opened through `ByteSource` using `O_RDONLY` (plus safe platform flags where available). Positional reads are used where supported. There is no source write API.

The application deliberately has no Save / Save As / overwrite / insert-byte / delete-byte / truncate / raw-device / process-memory path.

Export Selection writes selected bytes to a separate destination. It does not modify the inspected source and refuses unsafe source-target use according to the export helper contract.

Bookmarks are keyed from a content fingerprint and do not persist inspected source paths. Open Recent is deliberately absent.

Beespector Lite does not claim to prevent another process from changing a file while it is open. External-change detection is advisory and the UI recommends reload when a change is observed.
