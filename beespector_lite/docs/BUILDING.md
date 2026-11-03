# Building Beespector Lite

Portable source requires Python 3 and PyQt6. Install `beespector_lite/requirements.txt` in your preferred environment and run `python3 main.py`.

The Fedora AppImage helper is intentionally non-privileged. It never installs host packages or invokes elevation. Provide Python venv support and `appimagetool` yourself, then run:

`bash beespector_lite/packaging/fedora/build-appimage.sh`

The helper creates an isolated venv for build dependencies, runs QA, invokes PyInstaller, assembles the AppDir, validates the fixed Lite identity and emits a checksum beside the AppImage.
