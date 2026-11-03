import json, unittest
from pathlib import Path
from beespector_lite import APP_NAME, APP_VERSION, APP_ID, COMPONENT_ID, PACKAGE_NAME, EXECUTABLE_NAME, APPSTREAM_ID

class ContractTests(unittest.TestCase):
    @property
    def root(self): return Path(__file__).resolve().parents[2]

    def test_identity(self):
        self.assertEqual(APP_NAME,'Beespector Lite'); self.assertEqual(APP_VERSION,'0.0.4'); self.assertEqual(APP_ID,'beespector-lite'); self.assertEqual(COMPONENT_ID,'beespector-lite'); self.assertEqual(PACKAGE_NAME,'beespector_lite'); self.assertEqual(EXECUTABLE_NAME,'beespector-lite'); self.assertEqual(APPSTREAM_ID,'io.github.brunonlinespace.beespector-lite')
        identity=json.loads((self.root/'identity.json').read_text(encoding='utf-8')); self.assertEqual(identity['component_id'],'beespector-lite'); self.assertEqual(identity['package'],'beespector_lite')

    def test_byte_engine_has_no_write_flags(self):
        text=(self.root/'byte_source.py').read_text(encoding='utf-8'); self.assertIn('os.O_RDONLY',text)
        for forbidden in ('O_WRONLY','O_RDWR','pwrite(','truncate(','write('): self.assertNotIn(forbidden,text)

    def test_no_heavy_qt_modules(self):
        runtime=[self.root/n for n in ('app.py','command_bar.py','hex_view.py','dialogs.py','byte_source.py','search_engine.py','signatures.py','formatting.py','settings.py','color_engine.py','metadata.py')]
        text='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in runtime)
        for forbidden in ('QtWebEngine','QtPdf','QtPrintSupport'): self.assertNotIn(forbidden,text)

    def test_comparison_feature_is_absent(self):
        self.assertFalse((self.root/'compare_engine.py').exists()); self.assertFalse((self.root/'qa/tests/test_compare_engine.py').exists())
        app=(self.root/'app.py').read_text(encoding='utf-8').lower(); view=(self.root/'hex_view.py').read_text(encoding='utf-8').lower(); settings=(self.root/'settings.py').read_text(encoding='utf-8').lower()
        for forbidden in ('compare panel','open file to compare','compare now','comparison summary','difference index','previous difference','next difference','end comparison','make primary','ctrl + drop'): self.assertNotIn(forbidden,app)
        for forbidden in ('difference_provider','difference_ranges','logical_size_override','missing bytes'): self.assertNotIn(forbidden,view)
        self.assertNotIn('compare_index_limit',settings)

    def test_exp5_toolbar_architecture(self):
        app=(self.root/'app.py').read_text(encoding='utf-8'); command=(self.root/'command_bar.py').read_text(encoding='utf-8'); settings=(self.root/'settings.py').read_text(encoding='utf-8')
        self.assertNotIn('menuBar()',app); self.assertNotIn('class GlobalToolBar',app); self.assertNotIn('a_show_action_toolbar',app)
        for required in ("self.file_menu=self._make_action_menu('File'", "self.edit_menu=self._make_action_menu('Edit'", "self.inspect_menu=self._make_action_menu('Inspect'", "RaisedMenuToolbar((('File',window.file_menu),('Edit',window.edit_menu),('Inspect',window.inspect_menu),('View',window.view_menu),('Help',window.help_menu))", "setObjectName('MainToolbar')", "setObjectName('ShortcutToolbar')", "setObjectName('FindToolbar')", "self.pane.main_toolbar.show()", "'Shortcut Toolbar'", "'Find Bar'"):
            self.assertIn(required,app)
        self.assertNotIn("'main_toolbar_visible'",settings); self.assertNotIn("'action_toolbar_visible'",settings.split('def load_settings')[0])
        self.assertIn('class RaisedMenuToolbar',command); self.assertIn('ToolButtonPopupMode.InstantPopup',command); self.assertIn('ToolButtonTextOnly',command); self.assertIn('setAutoRaise(False)',command); self.assertIn('setFixedHeight(38)',command); self.assertIn('setMinimumWidth(68)',command)
        filepane=app[app.index('class FilePane'):app.index('class BeespectorWindow')]
        self.assertLess(filepane.index('lay.addWidget(self.main_toolbar,0)'),filepane.index('lay.addWidget(self.shortcut_toolbar,0)'))
        self.assertLess(filepane.index('lay.addWidget(self.shortcut_toolbar,0)'),filepane.index('lay.addWidget(self.view,1)'))
        self.assertLess(filepane.index('lay.addWidget(self.view,1)'),filepane.index('lay.addWidget(self.search_bar,0)'))

    def test_shortcut_toolbar_customization_and_filter(self):
        app=(self.root/'app.py').read_text(encoding='utf-8'); dialogs=(self.root/'dialogs.py').read_text(encoding='utf-8')
        self.assertIn('Add More Shortcuts…',app); self.assertIn('Reset Shortcut Toolbar',app); self.assertIn('ShortcutToolbarDialog',app)
        catalog=app[app.index('def _shortcut_toolbar_catalog'):app.index('def _shortcut_action_map')]
        for required in ('self.a_open','self.a_copy','self.a_inspector','self.a_find','self.a_status','self.a_docs'): self.assertIn(required,catalog)
        self.assertIn('Choose commands to show on the Shortcut Toolbar.',dialogs); self.assertIn('Main Toolbar remains dedicated to File / Edit / Inspect / View / Help menus',dialogs)
        filt=dialogs[dialogs.index('def _filter(self,text):'):dialogs.index('def selected_ids(self):')]; self.assertIn('item.setHidden(not visible)',filt); self.assertNotIn('.clear()',filt); self.assertNotIn('takeChild',filt)

    def test_drag_drop_labels(self):
        app=(self.root/'app.py').read_text(encoding='utf-8')
        self.assertIn("self.view_menu.addMenu('File Drag and Drop')",app); self.assertIn("('active','Opens on Active Window')",app); self.assertIn("('new','Opens on New Window')",app); self.assertNotIn("addMenu('Behaviour')",app); self.assertNotIn('Drop Default —',app)
        self.assertIn("if mods & Qt.KeyboardModifier.ShiftModifier: mode='new' if mode=='active' else 'active'",app); self.assertNotIn('Qt.KeyboardModifier.ControlModifier',app)

    def test_shortcut_revision(self):
        app=(self.root/'app.py').read_text(encoding='utf-8')
        for needle in ("'Alt+Return'","'Ctrl+E'","'Return'","'Shift+Return'","'Ctrl+Alt+I'","8:'Ctrl+1'","16:'Ctrl+2'","32:'Ctrl+3'"): self.assertIn(needle,app)
        for stale in ("'F2'","'F3'","'Shift+F3'","'Ctrl+Shift+1'","'Ctrl+Shift+2'","'Ctrl+Shift+3'"): self.assertNotIn(stale,app)
        self.assertIn("self.a_entropy=self._act('Entropy…',self.show_entropy,'Ctrl+E')",app)  # Ctrl+E Entropy

    def test_library_is_compact_vertical_and_stateful(self):
        app=(self.root/'app.py').read_text(encoding='utf-8'); dialogs=(self.root/'dialogs.py').read_text(encoding='utf-8')
        self.assertIn("QSplitter(Qt.Orientation.Vertical",dialogs); self.assertIn('setMinimumWidth(240)',app); self.assertIn('setMaximumWidth(420)',app); self.assertIn("self._library_close.setText('×')",app); self.assertIn("if layout==current and visible: self.settings['library_visible']=False",app)

    def test_compact_path_and_status_sync(self):
        app=(self.root/'app.py').read_text(encoding='utf-8'); self.assertIn("self._display=f'…/{parent}/{p.name}'",app); self.assertIn('self.setToolTip(self._path)',app); self.assertIn("'status_bar_visible':not self.statusBar().isHidden()",app)

    def test_no_custom_toolbar_icon_pack_was_ported(self):
        self.assertFalse((self.root/'assets'/'toolbar').exists()); self.assertFalse((self.root/'toolbar_icons.py').exists())

    def test_retained_inspection_features(self):
        app=(self.root/'app.py').read_text(encoding='utf-8')
        for term in ('Selection Inspector','Selected Range Checksums','Strings Finder','Repeated Byte Runs','Export Selection','Find All Current Search','Hex + Decimal','Add Bookmark','Manage Bookmarks','Copy Offset + Bytes','Byte Library…','Custom…'): self.assertIn(term,app)
        view=(self.root/'hex_view.py').read_text(encoding='utf-8'); self.assertIn('1 <= count <= 64',view); self.assertIn('_visible_block',view)

    def test_exp7_richer_file_knowledge_contract(self):
        from beespector_lite.signatures import SIGNATURES
        self.assertGreaterEqual(len(SIGNATURES),250)
        signatures=(self.root/'signatures.py').read_text(encoding='utf-8'); dialogs=(self.root/'dialogs.py').read_text(encoding='utf-8'); app=(self.root/'app.py').read_text(encoding='utf-8')
        self.assertIn('def identify_source',signatures); self.assertIn('auto_detect: bool = True',signatures)
        self.assertIn('Known extensions:',dialogs); self.assertIn('Detection:',dialogs); self.assertIn('Offset:',dialogs)
        self.assertIn('identify_source(new)',app); self.assertIn('identify_source(self.source)',app)

    def test_metadata_about_and_no_save_contracts(self):
        dialogs=(self.root/'dialogs.py').read_text(encoding='utf-8'); metadata=(self.root/'metadata.py').read_text(encoding='utf-8'); app=(self.root/'app.py').read_text(encoding='utf-8')
        self.assertIn('Friendly. Fast. Focused.',dialogs); self.assertIn('class KeyboardShortcutsDialog',dialogs); self.assertIn('class FileInfoDialog',dialogs); self.assertIn('Embedded Metadata',dialogs); self.assertNotIn('signatures, comparison and',dialogs)
        self.assertIn('metadata_snapshot',metadata); self.assertIn('O_RDONLY',metadata); self.assertNotIn('O_WRONLY',metadata)
        self.assertNotIn('Open Recent',app); self.assertNotIn('"Save"',app); self.assertNotIn('Save As',app)

if __name__=='__main__': unittest.main()
