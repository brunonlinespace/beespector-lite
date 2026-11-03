#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

APP_NAME="Beespector Lite"
APP_ID="beespector-lite"
APP_VERSION="0.0.4"
APPSTREAM_ID="io.github.brunonlinespace.beespector-lite"
DESKTOP_FILE_ID="${APPSTREAM_ID}.desktop"
OUTPUT_STEM="Beespector-Lite"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROGRAM_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
PROJECT_ROOT="$(cd -- "$PROGRAM_ROOT/.." && pwd -P)"
SOURCE_ENTRY="$PROJECT_ROOT/main.py"
COMPONENT_MANIFEST="$PROJECT_ROOT/suite-pythoine-component.json"
IDENTITY_MANIFEST="$PROGRAM_ROOT/identity.json"
SOURCE_MANIFEST="$PROGRAM_ROOT/SOURCE_MANIFEST.sha256"
RUNTIME_REQUIREMENTS="$PROGRAM_ROOT/requirements.txt"
BUILD_REQUIREMENTS="$PROGRAM_ROOT/packaging/pyinstaller/build-requirements.txt"
PYINSTALLER_SPEC="$PROGRAM_ROOT/packaging/pyinstaller/beespector-lite.spec"
APPIMAGE_PAYLOAD="$PROGRAM_ROOT/packaging/appimage"
RELEASE_CHECK="$PROGRAM_ROOT/qa/release_check.py"

HOST_ARCH_RAW="$(uname -m)"
case "$HOST_ARCH_RAW" in
    x86_64) HOST_ARCH="x86_64" ;;
    aarch64|arm64) HOST_ARCH="aarch64" ;;
    *) printf 'Error: unsupported build architecture: %s\n' "$HOST_ARCH_RAW" >&2; exit 2 ;;
esac
ARCH="${ARCH:-$HOST_ARCH}"

FEDORA_RELEASE="unknown"; HOST_NAME="unknown Linux"; OS_ID="unknown"
if [[ -r /etc/os-release ]]; then
    mapfile -d '' -t OS_RELEASE_VALUES < <(
        set +u
        source /etc/os-release
        printf '%s\0%s\0%s\0' "${ID:-unknown}" "${VERSION_ID:-unknown}" "${PRETTY_NAME:-unknown Linux}"
    )
    OS_ID="${OS_RELEASE_VALUES[0]:-unknown}"
    FEDORA_RELEASE="${OS_RELEASE_VALUES[1]:-unknown}"
    HOST_NAME="${OS_RELEASE_VALUES[2]:-unknown Linux}"
fi

BUILD_ROOT="${BUILD_ROOT:-$PROGRAM_ROOT/build/appimage-fedora${FEDORA_RELEASE}-${ARCH}}"
VENV="$BUILD_ROOT/venv"
PYI_DIST="$BUILD_ROOT/pyinstaller-dist"
PYI_WORK="$BUILD_ROOT/pyinstaller-work"
APPDIR="$BUILD_ROOT/BeespectorLite.AppDir"
SMOKE_HOME="$BUILD_ROOT/smoke-home"
DIST_DIR="${OUTPUT_DIR:-$PROGRAM_ROOT/dist}"
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/beespector-lite-appimage-tools"
APPIMAGE="$DIST_DIR/${OUTPUT_STEM}-${APP_VERSION}-${ARCH}.AppImage"
SHA_FILE="${APPIMAGE}.sha256"
BUILD_INFO="$DIST_DIR/${OUTPUT_STEM}-${APP_VERSION}-${ARCH}.build-info.txt"
PYTHON_LOCK="$DIST_DIR/${OUTPUT_STEM}-${APP_VERSION}-${ARCH}.build-python-lock.txt"
APPIMAGETOOL_RESOLVED=""
APPIMAGE_RUNTIME_RESOLVED=""
MAX_TOOL_BYTES=$((200 * 1024 * 1024))
export PYTHONDONTWRITEBYTECODE=1

log(){ printf '\n==> %s\n' "$*"; }
die(){ printf 'Error: %s\n' "$*" >&2; exit 1; }
require_file(){ [[ -f "$1" ]] || die "Missing file: $1"; }

validate_build_root(){
    local allowed_root resolved_root
    allowed_root="$(readlink -m -- "$PROGRAM_ROOT/build")"
    resolved_root="$(readlink -m -- "$BUILD_ROOT")"
    [[ "$resolved_root" != "$allowed_root" ]] || die "BUILD_ROOT must be a child beneath ${allowed_root}."
    case "$resolved_root" in "$allowed_root"/*) ;; *) die "Unsafe BUILD_ROOT outside ${allowed_root}: ${resolved_root}" ;; esac
}

clean_source_python_caches(){
    while IFS= read -r -d '' p; do rm -rf -- "$p"; done < <(
        find "$PROJECT_ROOT" \( -path "$PROGRAM_ROOT/build" -o -path "$PROGRAM_ROOT/dist" -o -path "$PROJECT_ROOT/.git" \) -prune -o -type d -name '__pycache__' -print0)
    while IFS= read -r -d '' p; do rm -f -- "$p"; done < <(
        find "$PROJECT_ROOT" \( -path "$PROGRAM_ROOT/build" -o -path "$PROGRAM_ROOT/dist" -o -path "$PROJECT_ROOT/.git" \) -prune -o -type f \( -name '*.pyc' -o -name '*.pyo' \) -print0)
}
cleanup(){ rm -rf "$SMOKE_HOME"; clean_source_python_caches; }
trap cleanup EXIT

check_non_privileged_policy(){
    if grep -Eq '^[[:space:]]*(sudo|dnf|pkexec|su)([[:space:]]|$)' "$0"; then
        die "Privilege-elevation or host-package-install command detected in builder."
    fi
}

check_host_prerequisites(){
    log "Checking non-privileged host prerequisites"
    local missing=() c
    for c in python3 bash timeout sha256sum od stat find grep cp ln chmod install mktemp rm mkdir mv tr awk date uname readlink sort env; do
        command -v "$c" >/dev/null 2>&1 || missing+=("$c")
    done
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then missing+=("curl-or-wget"); fi
    ((${#missing[@]}==0)) || die "Missing required host command(s): ${missing[*]}. The builder will not install system packages."
    python3 - <<'PY' >/dev/null 2>&1 || die "Python venv/ensurepip support is required."
import ensurepip, venv
PY
}

validate_component_manifest(){
    python3 - "$COMPONENT_MANIFEST" <<'PY'
import json, sys
from pathlib import Path
p=Path(sys.argv[1]); d=json.loads(p.read_text(encoding='utf-8'))
expected={
'id':'beespector-lite','name':'Beespector Lite','version':'0.0.4','component_kind':'reader',
'desktop_id':'io.github.brunonlinespace.beespector-lite','publisher_id':'brunonlinespace',
'repository':'https://github.com/brunonlinespace/beespector-lite','tagline':'Friendly. Fast. Focused.',
'extensions':[],'portable_command':['main.py'],
'capabilities':{'routing':False,'open':True,'create':False},
}
for k,v in expected.items():
    if d.get(k)!=v: raise SystemExit(f'Suite component manifest mismatch for {k}: {d.get(k)!r} != {v!r}')
PY
}

check_inputs(){
    validate_build_root
    if (( EUID == 0 )) && [[ "${BEESPECTOR_LITE_ALLOW_ROOT_BUILD:-0}" != "1" ]]; then die "Do not run the Beespector Lite AppImage builder with sudo/root."; fi
    case "$ARCH" in x86_64|aarch64) ;; *) die "Unsupported AppImage architecture: ${ARCH}" ;; esac
    [[ "$ARCH" == "$HOST_ARCH" ]] || die "Requested ${ARCH}, but host is ${HOST_ARCH_RAW}; cross-building is unsupported."
    if [[ "$OS_ID" != "fedora" || ! "$FEDORA_RELEASE" =~ ^(43|44)$ ]]; then
        [[ "${BEESPECTOR_LITE_ALLOW_UNSUPPORTED_HOST:-0}" == "1" ]] || die "Validated for Fedora 43/44. Detected ${HOST_NAME}."
        printf 'Warning: continuing on unsupported host: %s\n' "$HOST_NAME" >&2
    fi
    for p in "$SOURCE_ENTRY" "$COMPONENT_MANIFEST" "$IDENTITY_MANIFEST" "$SOURCE_MANIFEST" "$RUNTIME_REQUIREMENTS" "$BUILD_REQUIREMENTS" "$PYINSTALLER_SPEC" "$RELEASE_CHECK" \
        "$APPIMAGE_PAYLOAD/AppRun" "$APPIMAGE_PAYLOAD/$DESKTOP_FILE_ID" "$APPIMAGE_PAYLOAD/${APPSTREAM_ID}.metainfo.xml" "$PROGRAM_ROOT/LICENSE" "$PROGRAM_ROOT/assets/icons/beespector-512.png"; do require_file "$p"; done
    validate_component_manifest
}

run_source_release_qa(){
    log "Running Beespector Lite source release gate"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PROJECT_ROOT" python3 "$RELEASE_CHECK"
}

validate_desktop_entry_basic(){
    local d="$1"
    grep -Fqx '[Desktop Entry]' "$d" || die "Invalid desktop entry: $d"
    grep -Fqx 'Type=Application' "$d" || die "Desktop Entry requires Type=Application"
    grep -Fqx 'Name=Beespector Lite' "$d" || die "Desktop Entry requires Name=Beespector Lite"
    grep -Eq '^Exec=beespector-lite([[:space:]]|$)' "$d" || die "Desktop Entry requires Exec=beespector-lite"
    grep -Fqx 'Icon=beespector-lite' "$d" || die "Desktop Entry requires Icon=beespector-lite"
}

validate_appstream_basic(){
    python3 - "$1" "$APP_VERSION" <<'PY'
from pathlib import Path
import sys, xml.etree.ElementTree as ET
root=ET.parse(Path(sys.argv[1])).getroot(); version=sys.argv[2]
def text(q):
    n=root.find(q); return (n.text or '').strip() if n is not None else ''
assert text('id')=='io.github.brunonlinespace.beespector-lite'
assert text('name')=='Beespector Lite'
assert text('project_license')=='GPL-3.0-or-later'
assert text("launchable[@type='desktop-id']")=='io.github.brunonlinespace.beespector-lite.desktop'
dev=root.find("developer[@id='io.github.brunonlinespace']"); assert dev is not None and (dev.findtext('name') or '').strip()=='Bruno Machado'
urls={n.attrib.get('type'):(n.text or '').strip() for n in root.findall('url')}
assert urls.get('homepage')=='https://github.com/brunonlinespace/beespector-lite'
assert urls.get('bugtracker')=='https://github.com/brunonlinespace/beespector-lite/issues'
assert root.find("content_rating[@type='oars-1.1']") is not None
assert {(n.text or '').strip() for n in root.findall('./provides/binary')}=={'beespector-lite'}
assert 'application/octet-stream' in {(n.text or '').strip() for n in root.findall('./provides/mediatype')}
rels=root.findall('./releases/release'); assert len(rels)==1 and rels[0].attrib.get('version')==version
PY
}

prepare_environment(){
    log "Preparing isolated build environment"
    rm -rf "$BUILD_ROOT"; clean_source_python_caches; mkdir -p "$BUILD_ROOT" "$DIST_DIR" "$CACHE_DIR"; chmod 0700 "$CACHE_DIR"
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --disable-pip-version-check --upgrade pip wheel setuptools
    "$VENV/bin/python" -m pip install --disable-pip-version-check -r "$RUNTIME_REQUIREMENTS" -r "$BUILD_REQUIREMENTS"
    PYTHONPYCACHEPREFIX="$BUILD_ROOT/pycache" "$VENV/bin/python" -m compileall -q -x '/(build|dist)/' "$SOURCE_ENTRY" "$PROGRAM_ROOT"
    "$VENV/bin/python" -m pip check
    "$VENV/bin/python" -m pip freeze --all > "$PYTHON_LOCK"
    log "Running Beespector Lite release QA in build environment"
    PYTHONPATH="$PROJECT_ROOT" "$VENV/bin/python" -m unittest discover -s "$PROGRAM_ROOT/qa/tests" -p 'test_*.py'
    PYTHONPATH="$PROJECT_ROOT" "$VENV/bin/python" "$RELEASE_CHECK"
}

freeze_application(){
    log "Freezing Beespector Lite with PyInstaller"
    "$VENV/bin/python" -m PyInstaller --clean --noconfirm --distpath "$PYI_DIST" --workpath "$PYI_WORK" "$PYINSTALLER_SPEC"
    [[ -x "$PYI_DIST/beespector-lite/beespector-lite" ]] || die "PyInstaller executable was not created."
    local got; got="$(QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software "$PYI_DIST/beespector-lite/beespector-lite" --version)"
    [[ "$got" == "$APP_NAME $APP_VERSION" ]] || die "Frozen executable version mismatch: ${got}"
}

assemble_appdir(){
    log "Assembling AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib/beespector-lite" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/metainfo" "$APPDIR/usr/share/icons/hicolor/512x512/apps" "$APPDIR/usr/share/doc/beespector-lite"
    cp -a "$PYI_DIST/beespector-lite/." "$APPDIR/usr/lib/beespector-lite/"
    ln -s ../lib/beespector-lite/beespector-lite "$APPDIR/usr/bin/beespector-lite"
    install -m 0755 "$APPIMAGE_PAYLOAD/AppRun" "$APPDIR/AppRun"
    install -m 0644 "$APPIMAGE_PAYLOAD/$DESKTOP_FILE_ID" "$APPDIR/$DESKTOP_FILE_ID"
    install -m 0644 "$APPIMAGE_PAYLOAD/$DESKTOP_FILE_ID" "$APPDIR/usr/share/applications/$DESKTOP_FILE_ID"
    install -m 0644 "$APPIMAGE_PAYLOAD/${APPSTREAM_ID}.metainfo.xml" "$APPDIR/usr/share/metainfo/${APPSTREAM_ID}.metainfo.xml"
    install -m 0644 "$PROGRAM_ROOT/assets/icons/beespector-512.png" "$APPDIR/beespector-lite.png"
    install -m 0644 "$PROGRAM_ROOT/assets/icons/beespector-512.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/beespector-lite.png"
    ln -s beespector-lite.png "$APPDIR/.DirIcon"
    install -m 0644 "$PROGRAM_ROOT/LICENSE" "$APPDIR/usr/share/doc/beespector-lite/LICENSE"
    [[ -f "$PROGRAM_ROOT/docs/README.md" ]] && install -m 0644 "$PROGRAM_ROOT/docs/README.md" "$APPDIR/usr/share/doc/beespector-lite/README.md"
    [[ -f "$PROGRAM_ROOT/docs/RELEASE_NOTES.md" ]] && install -m 0644 "$PROGRAM_ROOT/docs/RELEASE_NOTES.md" "$APPDIR/usr/share/doc/beespector-lite/RELEASE_NOTES.md"
    validate_desktop_entry_basic "$APPDIR/$DESKTOP_FILE_ID"; validate_desktop_entry_basic "$APPDIR/usr/share/applications/$DESKTOP_FILE_ID"; validate_appstream_basic "$APPDIR/usr/share/metainfo/${APPSTREAM_ID}.metainfo.xml"
    if command -v desktop-file-validate >/dev/null 2>&1; then desktop-file-validate "$APPDIR/$DESKTOP_FILE_ID"; desktop-file-validate "$APPDIR/usr/share/applications/$DESKTOP_FILE_ID"; else printf 'Info: desktop-file-validate unavailable; built-in checks passed.\n' >&2; fi
    if command -v appstreamcli >/dev/null 2>&1; then appstreamcli validate --no-net "$APPDIR/usr/share/metainfo/${APPSTREAM_ID}.metainfo.xml"; else printf 'Info: appstreamcli unavailable; built-in AppStream checks passed.\n' >&2; fi
}

prepare_smoke_home(){ rm -rf "$SMOKE_HOME"; mkdir -p "$SMOKE_HOME/.config" "$SMOKE_HOME/.cache" "$SMOKE_HOME/.local/share"; }
run_version_smoke_test(){
    local label="$1"; shift; local f status; prepare_smoke_home; f="$(mktemp "${TMPDIR:-/tmp}/beespector-lite-version.XXXXXX.log")"; log "Running ${label} version smoke test"
    set +e; timeout 30s env HOME="$SMOKE_HOME" XDG_CONFIG_HOME="$SMOKE_HOME/.config" XDG_CACHE_HOME="$SMOKE_HOME/.cache" XDG_DATA_HOME="$SMOKE_HOME/.local/share" QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software "$@" --version >"$f" 2>&1; status=$?; set -e
    if [[ "$status" -ne 0 ]] || ! grep -Fxq "$APP_NAME $APP_VERSION" "$f"; then cat "$f" >&2; rm -f "$f"; die "${label} version smoke test failed with exit code ${status}."; fi; rm -f "$f"
}

validate_bundle(){
    log "Validating Beespector Lite Qt bundle"
    find "$APPDIR/usr/lib/beespector-lite" -name 'libqxcb.so' -print -quit | grep -q . || die "Qt XCB platform plugin was not bundled."
    find "$APPDIR/usr/lib/beespector-lite" \( -name 'libqwayland*.so' -o -name '*wayland*.so' \) -print -quit | grep -q . || printf 'Warning: Qt Wayland plugin was not detected; test XWayland carefully.\n' >&2
    # Beespector Lite's original spec deliberately excludes PrintSupport, QtPdf and WebEngine.
    # Do not turn incidental transitive libraries into cross-app functional assertions.
    run_version_smoke_test "AppDir" "$APPDIR/AppRun"
}

elf_sanity_check(){
    local label="$1" t="$2" m z
    require_file "$t"
    z="$(stat -c %s "$t")"
    [[ "$z" -gt 0 && "$z" -le "$MAX_TOOL_BYTES" ]] || die "${label} invalid size: ${z}"
    m="$(od -An -tx1 -N4 "$t" | tr -d ' \n')"
    [[ "$m" == 7f454c46 ]] || die "${label} is not ELF: $t"
}
download_elf_tool(){
    local label="$1" url="$2" dst="$3" part="${3}.part"
    [[ "$url" == https://* ]] || die "${label} URL must use HTTPS."
    rm -f "$part"
    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors --connect-timeout 30 --max-time 300 --max-filesize "$MAX_TOOL_BYTES" -o "$part" "$url"
    else
        wget --https-only --tries=3 --timeout=30 -O "$part" "$url"
    fi
    elf_sanity_check "$label" "$part"
    chmod 0755 "$part"
    mv -f "$part" "$dst"
}
prepare_appimagetool(){
    local t url; mkdir -p "$CACHE_DIR"; chmod 0700 "$CACHE_DIR"
    if [[ -n "${APPIMAGETOOL_PATH:-}" ]]; then t="$(readlink -f -- "$APPIMAGETOOL_PATH")"; [[ -x "$t" ]] || die "APPIMAGETOOL_PATH is not executable"; log "Using appimagetool supplied through APPIMAGETOOL_PATH"
    elif [[ -n "${APPIMAGETOOL:-}" ]]; then t="$(readlink -f -- "$APPIMAGETOOL")"; [[ -x "$t" ]] || die "APPIMAGETOOL is not executable"; log "Using appimagetool supplied through APPIMAGETOOL"
    elif command -v appimagetool >/dev/null 2>&1; then t="$(command -v appimagetool)"; log "Using appimagetool from PATH"
    else t="$CACHE_DIR/appimagetool-${ARCH}.AppImage"; url="${APPIMAGETOOL_URL:-https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage}"; if [[ ! -x "$t" ]]; then log "Downloading official appimagetool"; download_elf_tool "appimagetool" "$url" "$t"; else log "Using cached appimagetool"; fi; fi
    elf_sanity_check "appimagetool" "$t"
    if [[ -n "${APPIMAGETOOL_SHA256:-}" ]]; then [[ "$APPIMAGETOOL_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || die "APPIMAGETOOL_SHA256 must be 64 hexadecimal characters."; printf '%s  %s\n' "$APPIMAGETOOL_SHA256" "$t" | sha256sum --check --status || die "appimagetool SHA-256 verification failed."
    elif [[ "${BEESPECTOR_LITE_RELEASE_BUILD:-0}" == 1 ]]; then die "BEESPECTOR_LITE_RELEASE_BUILD=1 requires APPIMAGETOOL_SHA256."; else printf 'Warning: APPIMAGETOOL_SHA256 not supplied; resolved hash will be recorded.\n' >&2; fi
    APPIMAGETOOL_RESOLVED="$t"
}
prepare_appimage_runtime(){
    local t url; mkdir -p "$CACHE_DIR"; chmod 0700 "$CACHE_DIR"
    if [[ -n "${APPIMAGE_RUNTIME_PATH:-}" ]]; then
        t="$(readlink -f -- "$APPIMAGE_RUNTIME_PATH")"
        log "Using Type-2 runtime supplied through APPIMAGE_RUNTIME_PATH"
    elif [[ -n "${APPIMAGETOOL_RUNTIME_FILE:-}" ]]; then
        t="$(readlink -f -- "$APPIMAGETOOL_RUNTIME_FILE")"
        log "Using Type-2 runtime supplied through APPIMAGETOOL_RUNTIME_FILE"
    else
        t="$CACHE_DIR/runtime-${ARCH}"
        url="${APPIMAGE_RUNTIME_URL:-https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-${ARCH}}"
        if [[ ! -f "$t" ]]; then
            log "Downloading official AppImage Type-2 runtime"
            download_elf_tool "AppImage Type-2 runtime" "$url" "$t"
        else
            log "Using cached AppImage Type-2 runtime"
        fi
    fi
    elf_sanity_check "AppImage Type-2 runtime" "$t"
    if [[ -n "${APPIMAGE_RUNTIME_SHA256:-}" ]]; then
        [[ "$APPIMAGE_RUNTIME_SHA256" =~ ^[[:xdigit:]]{64}$ ]] || die "APPIMAGE_RUNTIME_SHA256 must be 64 hexadecimal characters."
        printf '%s  %s\n' "$APPIMAGE_RUNTIME_SHA256" "$t" | sha256sum --check --status || die "AppImage Type-2 runtime SHA-256 verification failed."
    elif [[ "${BEESPECTOR_LITE_RELEASE_BUILD:-0}" == 1 ]]; then
        die "BEESPECTOR_LITE_RELEASE_BUILD=1 requires APPIMAGE_RUNTIME_SHA256."
    else
        printf 'Warning: APPIMAGE_RUNTIME_SHA256 not supplied; resolved hash will be recorded.\n' >&2
    fi
    APPIMAGE_RUNTIME_RESOLVED="$t"
}

build_appimage(){
    log "Creating $(basename "$APPIMAGE")"
    rm -f "$APPIMAGE" "$SHA_FILE" "$BUILD_INFO"
    ARCH="$ARCH" "$APPIMAGETOOL_RESOLVED" --appimage-extract-and-run --runtime-file "$APPIMAGE_RUNTIME_RESOLVED" "$APPDIR" "$APPIMAGE"
    chmod 0755 "$APPIMAGE"
    # Preserve the finished AppImage path as one argument even when the managed Suite path contains spaces.
    run_version_smoke_test "final AppImage" "$APPIMAGE" --appimage-extract-and-run \
        || die "final AppImage version smoke test failed."
    sha256sum "$APPIMAGE" > "$SHA_FILE"
}
write_build_info(){
    local ah rh mh ih python_version pyinstaller_version
    ah="$(sha256sum "$APPIMAGETOOL_RESOLVED" | awk '{print $1}')"
    rh="$(sha256sum "$APPIMAGE_RUNTIME_RESOLVED" | awk '{print $1}')"
    mh="$(sha256sum "$COMPONENT_MANIFEST" | awk '{print $1}')"
    ih="$(sha256sum "$IDENTITY_MANIFEST" | awk '{print $1}')"
    # VENV can live beneath a Suite-managed path containing spaces. Quote the executable itself.
    python_version="$("$VENV/bin/python" --version 2>&1)"
    pyinstaller_version="$("$VENV/bin/python" -m PyInstaller --version)"
    { printf 'app=%s\nversion=%s\narch=%s\nhost=%s\npython=%s\npyinstaller=%s\nappimagetool=%s\nappimagetool_sha256=%s\nappimage_runtime=%s\nappimage_runtime_sha256=%s\ncomponent_manifest_sha256=%s\nidentity_manifest_sha256=%s\nsource_manifest=%s\n' \
        "$APP_NAME" "$APP_VERSION" "$ARCH" "$HOST_NAME" "$python_version" "$pyinstaller_version" \
        "$APPIMAGETOOL_RESOLVED" "$ah" "$APPIMAGE_RUNTIME_RESOLVED" "$rh" "$mh" "$ih" "$(basename "$SOURCE_MANIFEST")"; } > "$BUILD_INFO"
}

check_non_privileged_policy
check_host_prerequisites
check_inputs
run_source_release_qa
prepare_environment
freeze_application
assemble_appdir
validate_bundle
prepare_appimagetool
prepare_appimage_runtime
build_appimage
write_build_info
log "Build complete"
printf 'AppImage: %s\nChecksum: %s\nBuild information: %s\nPython lock: %s\n' "$APPIMAGE" "$SHA_FILE" "$BUILD_INFO" "$PYTHON_LOCK"
