from __future__ import annotations
from pathlib import Path
import hashlib, json, xml.etree.ElementTree as ET
from beespector_lite import (APP_NAME, APP_VERSION, APP_ID, COMPONENT_ID, PACKAGE_NAME,
    EXECUTABLE_NAME, APPSTREAM_ID, DESKTOP_FILE_ID, ORGANISATION, ORGANISATION_DOMAIN)

root=Path(__file__).resolve().parents[2]; pkg=root/'beespector_lite'; errors=[]
def need(cond,msg):
    if not cond: errors.append(msg)

need(APP_NAME=='Beespector Lite','wrong product name'); need(APP_VERSION=='0.0.4','wrong Lite version')
need(APP_ID==COMPONENT_ID=='beespector-lite','wrong component identity'); need(PACKAGE_NAME=='beespector_lite','wrong package identity'); need(EXECUTABLE_NAME=='beespector-lite','wrong executable identity'); need(APPSTREAM_ID=='io.github.brunonlinespace.beespector-lite','wrong AppStream identity'); need(DESKTOP_FILE_ID=='io.github.brunonlinespace.beespector-lite.desktop','wrong desktop identity'); need(ORGANISATION=='brunonlinespace' and ORGANISATION_DOMAIN=='brunonlinespace.github.io','wrong developer identity')
need(set(p.name for p in root.iterdir() if p.name!='__pycache__')=={'README.md','main.py','suite-pythoine-component.json','beespector_lite'},'portable root must contain README.md, main.py, suite-pythoine-component.json and beespector_lite/')
launcher=(root/'main.py').read_text(encoding='utf-8'); need('DEV_DROP_COMPONENT_ID: beespector-lite' in launcher,'missing safe Dev Drop recognition marker'); need('--component-id' in launcher,'missing component-id query')
identity=json.loads((pkg/'identity.json').read_text(encoding='utf-8')); need(identity.get('component_id')=='beespector-lite','identity.json component mismatch'); need(identity.get('package')=='beespector_lite','identity.json package mismatch')
component=json.loads((root/'suite-pythoine-component.json').read_text(encoding='utf-8'))
need(component.get('id')=='beespector-lite' and component.get('name')=='Beespector Lite','Suite component identity mismatch')
need(component.get('version')=='0.0.4' and component.get('component_kind')=='reader','Suite component version/kind mismatch')
need(component.get('extensions')==[] and component.get('portable_command')==['main.py'],'Suite component routing/portable contract mismatch')
need(component.get('repository')=='https://github.com/brunonlinespace/beespector-lite','Suite component repository mismatch')
need(component.get('tagline')=='Friendly. Fast. Focused.','Suite component tagline mismatch')
need(component.get('capabilities')=={'routing':False,'open':True,'create':False},'Suite component capabilities mismatch')

engine=(pkg/'byte_source.py').read_text(encoding='utf-8'); need('os.O_RDONLY' in engine,'byte source must use O_RDONLY')
for term in ('O_WRONLY','O_RDWR','os.pwrite','truncate('): need(term not in engine,f'forbidden write primitive in byte source: {term}')
app=(pkg/'app.py').read_text(encoding='utf-8'); app_lower=app.lower(); view=(pkg/'hex_view.py').read_text(encoding='utf-8'); settings=(pkg/'settings.py').read_text(encoding='utf-8'); dialogs=(pkg/'dialogs.py').read_text(encoding='utf-8'); command=(pkg/'command_bar.py').read_text(encoding='utf-8')
need('Open Recent' not in app,'privacy contract forbids Open Recent'); need('Save As' not in app and '"Save"' not in app,'GUI must not expose source save/write')
need("self.a_info=self._act('File Information / Metadata…',self.show_info,'Alt+Return')" in app,'Alt+Return File Information binding missing'); need("self.a_inspector=self._act('Selection Inspector…',self.show_selection_inspector,'Ctrl+I')" in app,'Ctrl+I inspector binding missing'); need("self.a_entropy=self._act('Entropy…',self.show_entropy,'Ctrl+E')" in app,'Ctrl+E Entropy binding missing')

need(not (pkg/'compare_engine.py').exists(),'Lite must not ship compare_engine.py'); need(not (pkg/'qa/tests/test_compare_engine.py').exists(),'Lite must not ship compare-engine tests')
for phrase in ('compare panel','open file to compare','compare now','comparison summary','difference index','previous difference','next difference','end comparison','make primary','ctrl + drop'): need(phrase not in app_lower,f'Lite UI still exposes comparison feature: {phrase}')
for phrase in ('set_difference_provider','_difference_ranges','logical_size_override','difference_mask'): need(phrase not in view,f'Lite HexView still contains comparison machinery: {phrase}')
need('compare_index_limit' not in settings,'Lite settings must not retain comparison index preference')

# exp5 fixed Main Toolbar + separate optional Shortcut Toolbar + lower Find Bar.
need('menuBar()' not in app,'Lite exp5 should use fixed toolbar surfaces rather than a QMenuBar')
need('class GlobalToolBar' not in app,'old mixed Global Toolbar must be removed')
need('a_show_action_toolbar' not in app,'old Action Toolbar visibility action must be removed')
for term in ("self.file_menu=self._make_action_menu('File'","self.edit_menu=self._make_action_menu('Edit'","self.inspect_menu=self._make_action_menu('Inspect'","RaisedMenuToolbar((('File',window.file_menu),('Edit',window.edit_menu),('Inspect',window.inspect_menu),('View',window.view_menu),('Help',window.help_menu))","setObjectName('MainToolbar')","setObjectName('ShortcutToolbar')","setObjectName('FindToolbar')","self.pane.main_toolbar.show()",'Add More Shortcuts…','Reset Shortcut Toolbar','Shortcut Toolbar','Find Bar'):
    need(term in app,f'missing exp5 toolbar architecture: {term}')
for term in ('class RaisedMenuToolbar','ToolButtonPopupMode.InstantPopup','ToolButtonTextOnly','setAutoRaise(False)','setFixedHeight(38)','setMinimumWidth(68)'):
    need(term in command,f'missing classic raised menu-button contract: {term}')
for stale in ('QTabBar','QStackedWidget','QScrollArea','WA_AcceptTouchEvents','def wheelEvent','TouchUpdate'):
    need(stale not in command,f'tabbed/ribbon Action UI remains: {stale}')
filepane=app[app.index('class FilePane'):app.index('class BeespectorWindow')]
need(filepane.index('lay.addWidget(self.main_toolbar,0)')<filepane.index('lay.addWidget(self.shortcut_toolbar,0)'),'Main Toolbar must precede Shortcut Toolbar')
need(filepane.index('lay.addWidget(self.shortcut_toolbar,0)')<filepane.index('lay.addWidget(self.view,1)'),'Shortcut Toolbar must stay above view')
need(filepane.index('lay.addWidget(self.view,1)')<filepane.index('lay.addWidget(self.search_bar,0)'),'Find bar must stay below file view')
need("'main_toolbar_visible'" not in settings,'Main Toolbar visibility must not be persisted'); need("'action_toolbar_visible': True" not in settings,'old Action Toolbar setting must not remain in defaults')
need("'shortcut_toolbar_visible': True" in settings and "'shortcut_toolbar_shortcuts': []" in settings,'Shortcut Toolbar settings missing')
need("raw.get('global_toolbar_shortcuts', [])" in settings,'old custom shortcuts must migrate to Shortcut Toolbar')

# Shortcut toolbar can contain commands from all command areas.
need('class ShortcutToolbarDialog' in dialogs,'Shortcut Toolbar chooser missing'); need('Choose commands to show on the Shortcut Toolbar.' in dialogs,'Shortcut Toolbar chooser note missing')
catalog=app[app.index('def _shortcut_toolbar_catalog'):app.index('def _shortcut_action_map')]
for action in ('self.a_open','self.a_copy','self.a_inspector','self.a_find','self.a_status','self.a_docs'): need(action in catalog,f'Shortcut Toolbar catalog missing {action}')
filt=dialogs[dialogs.index('def _filter(self,text):'):dialogs.index('def selected_ids(self):')]; need('item.setHidden(not visible)' in filt,'shortcut search must filter stable items in place'); need('.clear()' not in filt and 'takeChild' not in filt,'shortcut search must not destructively rebuild tree')

# Requested drag/drop terminology.
need("self.view_menu.addMenu('File Drag and Drop')" in app,'File Drag and Drop submenu missing'); need("('active','Opens on Active Window')" in app,'active-window drag label missing'); need("('new','Opens on New Window')" in app,'new-window drag label missing'); need("addMenu('Behaviour')" not in app,'old Behaviour submenu remains'); need('Drop Default —' not in app,'old drag labels remain'); need('Qt.KeyboardModifier.ControlModifier' not in app,'Lite must not give Ctrl+Drop comparison semantics')

for shortcut in ("'Alt+Return'","'Ctrl+E'","'Return'","'Shift+Return'","'Ctrl+Alt+I'","8:'Ctrl+1'","16:'Ctrl+2'","32:'Ctrl+3'"): need(shortcut in app,f'missing shortcut {shortcut}')
for stale in ("'F2'","'F3'","'Shift+F3'","'Ctrl+Shift+1'","'Ctrl+Shift+2'","'Ctrl+Shift+3'"): need(stale not in app,f'stale shortcut remains {stale}')
need("colours.addAction(self.colour_actions['off']); colours.addSeparator()" in app,'Text Colours separator missing'); need("self.view_menu.addAction(self.a_columns); self.view_menu.addSeparator()" in app,'Column Identifiers separator missing')

# Library and path contracts.
need('QSplitter(Qt.Orientation.Vertical' in dialogs,'Byte Library list/details must be top/bottom adjustable'); need('setMinimumWidth(240)' in app and 'setMaximumWidth(420)' in app,'Byte Library sidebar width bounds missing'); need("self._library_close.setText('×')" in app,'Byte Library sidebar close button missing'); need("if layout==current and visible: self.settings['library_visible']=False" in app,'Library placement shortcuts are not toggles')
need("self._display=f'…/{parent}/{p.name}'" in app and 'self.setToolTip(self._path)' in app,'compact path + full tooltip contract missing'); need("'status_bar_visible':not self.statusBar().isHidden()" in app,'status-bar persistence must use local hidden state')

# No mainline toolbar/custom artwork is ported. Existing Lite app artwork stays exact.
need(not (pkg/'assets'/'toolbar').exists(),'Lite must not ship mainline toolbar icon pack'); need(not (pkg/'toolbar_icons.py').exists(),'Lite must not ship toolbar icon helper')
master=pkg/'assets/icons/beespector-master.png'; need(master.is_file(),'missing Lite master logo')
if master.is_file(): need(hashlib.sha256(master.read_bytes()).hexdigest()=='dc309e4b1f4b5e0c37ccaf4008998b397b50ea51a929529f103e0f39a9f8161a','Lite application logo changed')
for size in (16,24,32,48,64,128,256,512): need((pkg/f'assets/icons/beespector-{size}.png').is_file(),f'missing {size}px Lite icon')

for term in ('Selection Inspector','Selected Range Checksums','Strings Finder','Repeated Byte Runs','Export Selection','Find All Current Search','Copy Offset + Bytes','Hex + Decimal','Add Bookmark','Manage Bookmarks','Byte Library…','Custom…'): need(term in app,f'missing retained inspection feature: {term}')
need('1 <= count <= 64' in view and '_visible_block' in view,'HexView 1-64/cache contract missing')
need('Friendly. Fast. Focused.' in dialogs,'About slogan changed'); need('signatures, comparison and' not in dialogs,'Lite About must not describe comparison'); need('class ByteLibraryWidget' in dialogs,'Byte Library missing'); need('class FileInfoDialog' in dialogs and 'Embedded Metadata' in dialogs,'metadata dialog missing')
signatures=(pkg/'signatures.py').read_text(encoding='utf-8')
need('def identify_source' in signatures,'source-aware signature detector missing')
need('auto_detect: bool = True' in signatures,'conservative signature detection flag missing')
need('def offset_text' in signatures and 'def extensions_text' in signatures,'rich signature presentation helpers missing')
try:
    from beespector_lite.signatures import SIGNATURES
    need(len(SIGNATURES)>=250,'rich Byte Library must contain at least 250 signatures')
except Exception as exc:
    need(False,f'could not inspect signature catalogue: {exc}')
need('Known extensions:' in dialogs and 'Detection:' in dialogs and 'Offset:' in dialogs,'rich Byte Library detail fields missing')
metadata=(pkg/'metadata.py').read_text(encoding='utf-8')
for term in ('filesystem_metadata','identification_metadata','embedded_metadata','metadata_snapshot','Extended attributes','PNG image','ELF','ZIP archive'): need(term in metadata,f'metadata engine missing {term}')
for term in ('O_WRONLY','O_RDWR','pwrite(','truncate('): need(term not in metadata,f'metadata engine must remain read-only: {term}')

# Packaging identity/version.
desktop=pkg/'packaging/appimage/io.github.brunonlinespace.beespector-lite.desktop'; meta=pkg/'packaging/appimage/io.github.brunonlinespace.beespector-lite.metainfo.xml'; spec=pkg/'packaging/pyinstaller/beespector-lite.spec'
need(desktop.is_file(),'missing canonical Lite desktop file'); need(meta.is_file(),'missing Lite AppStream metadata'); need(spec.is_file(),'missing Lite PyInstaller spec')
if meta.is_file():
    ET.parse(meta); xml=meta.read_text(encoding='utf-8')
    need('<release version="0.0.4"' in xml,'AppStream version mismatch')
    need('<developer id="io.github.brunonlinespace"><name>Bruno Machado</name></developer>' in xml,'AppStream developer metadata missing')
    need('<url type="homepage">https://github.com/brunonlinespace/beespector-lite</url>' in xml,'AppStream homepage missing')
    need('<url type="bugtracker">https://github.com/brunonlinespace/beespector-lite/issues</url>' in xml,'AppStream bugtracker missing')
    need('<content_rating type="oars-1.1"' in xml,'AppStream content rating missing')
    need('<binary>beespector-lite</binary>' in xml,'AppStream binary provider missing')
if spec.is_file():
    t=spec.read_text(encoding='utf-8'); need('program_root=project_root/"beespector_lite"' in t,'spec package root mismatch'); need('name="beespector-lite"' in t,'spec executable mismatch'); need('collect_submodules("beespector_lite")' in t,'spec hidden import mismatch')
builder=(pkg/'packaging/fedora/build-appimage.sh').read_text(encoding='utf-8')
for cmd in ('sudo ','dnf ','pkexec ',' su '): need(cmd not in builder,f'non-privileged builder contains {cmd.strip()}')
need('APP_VERSION="0.0.4"' in builder,'builder version mismatch')
need((pkg/'packaging/pyinstaller/build-requirements.txt').is_file(),'canonical PyInstaller build requirements missing')
need(not (pkg/'packaging/fedora/requirements-build.txt').exists(),'legacy Fedora build-requirements location remains')
for term in ('validate_build_root','pip check','pip freeze --all','validate_component_manifest','appstreamcli validate --no-net','APPIMAGETOOL_SHA256','APPIMAGE_RUNTIME_SHA256','prepare_appimage_runtime','--runtime-file "$APPIMAGE_RUNTIME_RESOLVED"','run_version_smoke_test "final AppImage"'):
    need(term in builder,f'hardened AppImage builder contract missing: {term}')
need('https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-${ARCH}' in builder,'explicit Type-2 runtime source missing')
need('appimage_runtime_sha256=' in builder,'build info does not record Type-2 runtime hash')
need('run_version_smoke_test "final AppImage" "$APPIMAGE" --appimage-extract-and-run' in builder,'final AppImage path is not quoted in smoke test')
need('|| die "final AppImage version smoke test failed."' in builder,'final AppImage smoke-test failure is not explicitly fatal')
need('python_version="$("$VENV/bin/python" --version 2>&1)"' in builder,'build-info Python probe does not quote VENV path')
need('pyinstaller_version="$("$VENV/bin/python" -m PyInstaller --version)"' in builder,'build-info PyInstaller probe does not quote VENV path')

# Manifest.
manifest=pkg/'SOURCE_MANIFEST.sha256'
if manifest.is_file():
    expected={}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        if line.strip(): digest,rel=line.split('  ',1); expected[rel]=digest
    actual={}
    for path in root.rglob('*'):
        if not path.is_file(): continue
        rel=path.relative_to(root).as_posix()
        if rel=='beespector_lite/SOURCE_MANIFEST.sha256' or '__pycache__' in rel or rel.endswith('.pyc') or rel.endswith('.pyo'): continue
        if rel.startswith('beespector_lite/build/') or rel.startswith('beespector_lite/dist/'): continue
        actual[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
    need(set(expected)==set(actual),'source manifest file list mismatch')
    for rel,digest in actual.items(): need(expected.get(rel)==digest,f'source manifest hash mismatch: {rel}')
else: need(False,'missing source manifest')

if errors:
    print('RELEASE CHECK: FAIL'); [print(' -',e) for e in errors]; raise SystemExit(1)
print('RELEASE CHECK: PASS')
