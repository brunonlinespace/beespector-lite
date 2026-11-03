from __future__ import annotations
import os, sys
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread, QUrl, QByteArray, QSize
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices, QFont, QFontDatabase, QFontMetrics, QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,QComboBox,QDialog,QFileDialog,QFontDialog,QHBoxLayout,QLabel,QLineEdit,QMainWindow,QMessageBox,
    QPushButton,QSizePolicy,QStyle,QToolBar,QToolButton,QVBoxLayout,QWidget,QInputDialog,QProgressDialog,QSplitter,
    QFrame,QMenu
)
from . import APP_NAME, APP_VERSION, APP_ID, APPSTREAM_ID, ORGANISATION, ORGANISATION_DOMAIN
from .byte_source import ByteSource
from .search_engine import find_forward, find_backward, find_all, parse_hex_pattern, encode_text_pattern
from .signatures import identify_source
from .formatting import human_size
from .settings import load_settings, save_settings, config_path
from .hex_view import HexView
from .analysis_tools import selection_interpretation, range_checksums, range_entropy, entropy_description, find_printable_strings, find_repeated_runs, export_range
from .bookmarks import BookmarkStore, source_fingerprint
from .dialogs import (
    GoToDialog, ByteLibraryDialog, ByteLibraryWidget, FileInfoDialog, TextDialog, AboutDialog, GITHUB_URL,
    SelectionInspectorDialog, OffsetResultsDialog, BookmarkDialog, SimpleReportDialog, KeyboardShortcutsDialog,
    ShortcutToolbarDialog,
)
from .command_bar import RaisedMenuToolbar

PROGRAM_ROOT=Path(__file__).resolve().parent
ICON_PATH=PROGRAM_ROOT/'assets'/'icons'/'beespector.png'
WINDOWS=[]


class SearchWorker(QObject):
    done=pyqtSignal(object,int); failed=pyqtSignal(str)
    def __init__(self,path,pattern,start,direction): super().__init__(); self.path=path; self.pattern=pattern; self.start=start; self.direction=direction
    def run(self):
        try:
            with ByteSource(self.path) as s:
                cancel=lambda:QThread.currentThread().isInterruptionRequested()
                result=find_forward(s,self.pattern,self.start,cancelled=cancel) if self.direction=='forward' else find_backward(s,self.pattern,self.start,cancelled=cancel)
            self.done.emit(result,len(self.pattern))
        except Exception as e: self.failed.emit(str(e))


class AnalysisWorker(QObject):
    done=pyqtSignal(str,object); failed=pyqtSignal(str,str)
    def __init__(self,path,kind,args): super().__init__(); self.path=path; self.kind=kind; self.args=dict(args)
    def run(self):
        try:
            with ByteSource(self.path) as source:
                cancel=lambda:QThread.currentThread().isInterruptionRequested()
                if self.kind=='find_all': result=find_all(source,self.args['pattern'],self.args.get('start',0),max_results=self.args.get('max_results',10000),cancelled=cancel)
                elif self.kind=='strings': result=find_printable_strings(source,self.args.get('minimum',4),max_results=self.args.get('max_results',10000),cancelled=cancel)
                elif self.kind=='runs': result=find_repeated_runs(source,self.args.get('minimum',16),max_results=self.args.get('max_results',10000),cancelled=cancel)
                elif self.kind=='checksums': result=range_checksums(source,self.args['start'],self.args['length'],cancelled=cancel)
                elif self.kind=='entropy': result=range_entropy(source,self.args['start'],self.args['length'],cancelled=cancel)
                else: raise ValueError(f'Unknown analysis kind: {self.kind}')
            self.done.emit(self.kind,result)
        except Exception as exc: self.failed.emit(self.kind,str(exc))


class SearchBar(QWidget):
    requested=pyqtSignal(str,str,str); queryEdited=pyqtSignal(str,str); findAllRequested=pyqtSignal(str,str)
    def __init__(self,parent=None):
        super().__init__(parent); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        lay=QHBoxLayout(self); lay.setContentsMargins(2,2,2,2); lay.setSpacing(6)
        self.mode=QComboBox(self); self.mode.addItem('Text','text'); self.mode.addItem('Hex','hex'); self.mode.setToolTip('Search as UTF-8 text or hexadecimal bytes'); self.mode.setFixedWidth(118)
        self.entry=QLineEdit(self); self.entry.setPlaceholderText('Find text (UTF-8)'); self.entry.setMinimumWidth(180); self.entry.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.find=QPushButton(self); self.find.setToolTip('Find next'); self.find.setFixedSize(38,30)
        self.prev=QToolButton(self); self.prev.setToolTip('Find previous'); self.prev.setFixedSize(34,30); self.prev.setAutoRaise(False)
        self.next=QToolButton(self); self.next.setToolTip('Find next'); self.next.setFixedSize(34,30); self.next.setAutoRaise(False)
        self.find_all=QToolButton(self); self.find_all.setToolTip('Find all matches in this file'); self.find_all.setFixedSize(34,30); self.find_all.setAutoRaise(False)
        style=self.style(); self.find.setIcon(QIcon.fromTheme('edit-find',style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))); self.prev.setIcon(QIcon.fromTheme('go-previous',style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack))); self.next.setIcon(QIcon.fromTheme('go-next',style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward))); self.find_all.setIcon(QIcon.fromTheme('edit-find-all',style.standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)))
        lay.addWidget(self.mode); lay.addWidget(self.entry,1); lay.addWidget(self.find); lay.addWidget(self.prev); lay.addWidget(self.next); lay.addWidget(self.find_all)
        self.mode.currentIndexChanged.connect(self._changed); self.entry.textChanged.connect(self._changed); self.entry.returnPressed.connect(lambda:self._request('forward')); self.find.clicked.connect(lambda:self._request('forward')); self.prev.clicked.connect(lambda:self._request('backward')); self.next.clicked.connect(lambda:self._request('forward')); self.find_all.clicked.connect(lambda:self.findAllRequested.emit(str(self.mode.currentData() or 'text'),self.entry.text())); self._changed()
    def _changed(self,*_):
        mode=str(self.mode.currentData() or 'text'); self.entry.setPlaceholderText('Find text (UTF-8)' if mode=='text' else 'Hex bytes: 89 50 4E 47'); self.queryEdited.emit(mode,self.entry.text())
    def _request(self,direction): self.requested.emit(str(self.mode.currentData() or 'text'),self.entry.text(),direction)
    def focus_entry(self): self.entry.setFocus(); self.entry.selectAll()
    def state(self): return str(self.mode.currentData() or 'text'), self.entry.text()


class ElidedPathLabel(QLabel):
    """Display only …/parent/file; full absolute path remains in tooltip."""
    def __init__(self,parent=None):
        super().__init__(parent); self._path=''; self._display='No file selected'; self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
    def set_path(self,path):
        if not path:
            self._path=''; self._display='No file selected'; self.setToolTip(''); self._refresh(); return
        p=Path(path); self._path=str(p); parent=p.parent.name; self._display=f'…/{parent}/{p.name}' if parent else f'…/{p.name}'; self.setToolTip(self._path); self._refresh()
    def resizeEvent(self,event): super().resizeEvent(event); self._refresh()
    def _refresh(self):
        metrics=QFontMetrics(self.font()); self.setText(metrics.elidedText(self._display,Qt.TextElideMode.ElideLeft,max(40,self.width()-4)))


class FilePane(QWidget):
    """Single-file pane with fixed Main Toolbar, optional Shortcut Toolbar and lower Find Bar."""
    def __init__(self,window,view,parent=None):
        super().__init__(parent); self.window=window; self.view=view; self.source=None
        lay=QVBoxLayout(self); lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        self.main_toolbar=RaisedMenuToolbar((('File',window.file_menu),('Edit',window.edit_menu),('Inspect',window.inspect_menu),('View',window.view_menu),('Help',window.help_menu)),self); self.main_toolbar.setObjectName('MainToolbar'); self.main_toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.main_toolbar.customContextMenuRequested.connect(lambda pos:window._show_toolbar_context(self.main_toolbar.mapToGlobal(pos))); lay.addWidget(self.main_toolbar,0)
        self.shortcut_toolbar=QToolBar(self); self.shortcut_toolbar.setObjectName('ShortcutToolbar'); self.shortcut_toolbar.setMovable(False); self.shortcut_toolbar.setFloatable(False); self.shortcut_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly); self.shortcut_toolbar.setFixedHeight(38); self.shortcut_toolbar.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        self.shortcut_toolbar.setStyleSheet('QToolBar { border: 0; spacing: 2px; background: transparent; } QToolButton { border: 0; padding: 4px 7px; margin: 0; background: transparent; } QToolButton:hover { border: 1px solid palette(mid); border-radius: 3px; background: palette(midlight); } QToolButton:pressed, QToolButton:checked { border: 1px solid palette(dark); border-radius: 3px; background: palette(mid); }')
        self.shortcut_toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.shortcut_toolbar.customContextMenuRequested.connect(lambda pos:window._show_toolbar_context(self.shortcut_toolbar.mapToGlobal(pos))); lay.addWidget(self.shortcut_toolbar,0)
        header=QWidget(self); hl=QHBoxLayout(header); hl.setContentsMargins(5,3,5,3); hl.setSpacing(5); label=QLabel('File:',header); label.setStyleSheet('font-weight: 600;'); self.path_label=ElidedPathLabel(header); hl.addWidget(label,0); hl.addWidget(self.path_label,1); lay.addWidget(header,0)
        self.view.setParent(self); lay.addWidget(self.view,1)
        self.search_bar=SearchBar(self); self.search_bar.setObjectName('FindToolbar'); self.search_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.search_bar.customContextMenuRequested.connect(lambda pos:window._show_toolbar_context(self.search_bar.mapToGlobal(pos))); lay.addWidget(self.search_bar,0)
        self.search_bar.requested.connect(window.search_from_bar); self.search_bar.findAllRequested.connect(window.find_all_from_bar)
        self.view.cursorChanged.connect(window._update_position); self.view.selectionChanged.connect(window._update_position)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.view.customContextMenuRequested.connect(lambda pos:window._show_toolbar_context(self.view.mapToGlobal(pos)))
    def set_source(self,source):
        self.source=source; self.view.set_source(source); self.path_label.set_path(source.path if source else None)
    def set_shortcut_actions(self,actions):
        self.shortcut_toolbar.clear()
        for action in actions: self.shortcut_toolbar.addAction(action)


class BeespectorWindow(QMainWindow):
    def __init__(self,initial: str|None=None):
        super().__init__(); self.settings=load_settings(); self.source:ByteSource|None=None; self._search_thread=None; self._search_worker=None; self._analysis_thread=None; self._analysis_worker=None; self._last_pattern=None; self._external_warned=False; self._restoring_ui=True; self.bookmark_store=BookmarkStore(); self._bookmark_fingerprint=None; self._library_sidebar_width=max(240,min(420,int(self.settings.get('library_sidebar_width',320))))
        WINDOWS.append(self); self.setWindowTitle(APP_NAME); self.setObjectName('BeespectorLiteWindow'); self.setProperty('componentId',APP_ID); self.resize(1120,720); self.setAcceptDrops(True)
        if ICON_PATH.exists(): self.setWindowIcon(QIcon(str(ICON_PATH)))
        # Lite exp5 consolidates every menu into the fixed Main Toolbar and
        # keeps user-selected commands in a separate optional Shortcut Toolbar.
        self.view=HexView(self); self._apply_view_settings(); self._make_status(); self._make_actions(); self._make_toolbar_menus(); self._make_dialogs(); self._make_central(); self._restore_ui(); self._restoring_ui=False; self._update_enabled()
        self.timer=QTimer(self); self.timer.setInterval(2000); self.timer.timeout.connect(self._check_external); self.timer.start()
        if initial: QTimer.singleShot(0,lambda:self.open_path(initial))

    def _open_new_window(self,path):
        w=BeespectorWindow(str(path)); w.show(); w.raise_(); w.activateWindow(); return w

    def _apply_view_settings(self):
        self.view.set_bytes_per_row(self.settings['bytes_per_row']); self.view.set_show_ascii(self.settings['show_ascii']); self.view.set_show_offset(self.settings['show_offset']); self.view.set_show_column_identifiers(self.settings.get('show_column_identifiers',True)); self.view.set_canvas_scheme(self.settings['canvas_scheme']); self.view.set_text_colour_mode(self.settings['text_colour_mode']); self.view.set_offset_mode(self.settings.get('offset_mode','hex'))
        font=QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        if self.settings.get('font_family'): font.setFamily(self.settings['font_family'])
        font.setPointSize(self.settings['font_size']); requested=int(self.settings.get('font_weight',400)); allowed=[100,200,300,400,500,600,700,800,900]; font.setWeight(QFont.Weight(min(allowed,key=lambda value:abs(value-requested)))); font.setItalic(self.settings.get('font_italic',False)); self.view.set_display_font(font)

    def _act(self,text,slot,shortcut=None,checkable=False):
        a=QAction(text,self); a.triggered.connect(slot); a.setCheckable(checkable)
        if shortcut: a.setShortcut(QKeySequence(shortcut))
        return a

    def _make_actions(self):
        self.a_open=self._act('Open…',self.open_dialog,'Ctrl+O'); self.a_reload=self._act('Reload',self.reload_file,'F5'); self.a_close=self._act('Close File',self.close_file,'Ctrl+W'); self.a_info=self._act('File Information / Metadata…',self.show_info,'Alt+Return'); self.a_exit=self._act('Exit',self.close,'Ctrl+Q')
        self.a_select_all=self._act('Select All',self.view.select_all,'Ctrl+A'); self.a_copy=self._act('Copy Hex',lambda:self.view.copy_selection('hex'),'Ctrl+C'); self.a_copy_compact=self._act('Copy Compact Hex',lambda:self.view.copy_selection('compact')); self.a_copy_escaped=self._act('Copy Escaped Bytes',lambda:self.view.copy_selection('escaped')); self.a_copy_ascii=self._act('Copy ASCII',lambda:self.view.copy_selection('ascii')); self.a_copy_offset=self._act('Copy Offset',self.view.copy_offset); self.a_copy_offset_bytes=self._act('Copy Offset + Bytes',self.view.copy_offset_and_bytes,'Ctrl+Shift+C'); self.a_export=self._act('Export Selection…',self.export_selection,'Ctrl+Shift+E')
        self.a_inspector=self._act('Selection Inspector…',self.show_selection_inspector,'Ctrl+I'); self.a_checksums=self._act('Selected Range Checksums…',self.show_selection_checksums); self.a_entropy=self._act('Entropy…',self.show_entropy,'Ctrl+E'); self.a_goto=self._act('Go to Offset…',self.show_goto,'Ctrl+G'); self.a_strings=self._act('Strings Finder…',self.show_strings,'Ctrl+Alt+S'); self.a_runs=self._act('Repeated Byte Runs…',self.show_repeated_runs); self.a_add_bookmark=self._act('Add Bookmark…',self.add_bookmark,'Ctrl+B'); self.a_bookmarks=self._act('Manage Bookmarks…',self.show_bookmarks,'Ctrl+Shift+B')
        self.a_find=self._act('Find',self.focus_find,'Ctrl+F'); self.a_next=self._act('Find Next',lambda:self.repeat_find('forward'),'Return'); self.a_prev=self._act('Find Previous',lambda:self.repeat_find('backward'),'Shift+Return'); self.a_find_all=self._act('Find All Current Search…',self.find_all_current,'Ctrl+Shift+F')
        self.a_status=self._act('Status Bar',self.toggle_status_bar,checkable=True); self.a_status.setChecked(bool(self.settings.get('status_bar_visible',True)))
        self.a_ascii=self._act('Show ASCII',self.toggle_ascii,'Ctrl+Alt+A',checkable=True); self.a_ascii.setChecked(self.settings['show_ascii']); self.a_offset=self._act('Show Offset',self.toggle_offset,'Ctrl+Alt+O',checkable=True); self.a_offset.setChecked(self.settings['show_offset']); self.a_columns=self._act('Show Column Identifiers',self.toggle_column_identifiers,'Ctrl+Alt+I',checkable=True); self.a_columns.setChecked(self.settings.get('show_column_identifiers',True))
        self.a_zoom_in=self._act('Increase Font Size',lambda:self.zoom(1),'Ctrl++'); self.a_zoom_out=self._act('Decrease Font Size',lambda:self.zoom(-1),'Ctrl+-'); self.a_zoom_reset=self._act('Reset Font Size',self.zoom_reset,'Ctrl+0'); self.a_font=self._act('Display Font…',self.choose_font); self.a_custom_bpr=self._act('Custom…',self.custom_bpr)
        self.a_library=self._act('Byte Library…',self.show_library,'Ctrl+L',checkable=True); self.a_library.setChecked(bool(self.settings.get('library_visible',False)))
        self.offset_mode_group=QActionGroup(self); self.offset_mode_group.setExclusive(True); self.offset_mode_actions={}
        for key,label in (('hex','Hexadecimal'),('decimal','Decimal'),('both','Hex + Decimal')):
            a=self._act(label,lambda _=False,k=key:self.set_offset_mode(k),checkable=True); a.setChecked(self.settings.get('offset_mode','hex')==key); self.offset_mode_group.addAction(a); self.offset_mode_actions[key]=a
        self.bpr_group=QActionGroup(self); self.bpr_group.setExclusive(False); self.bpr_actions={}
        for n in (8,16,32):
            shortcut={8:'Ctrl+1',16:'Ctrl+2',32:'Ctrl+3'}[n]; a=self._act(str(n),lambda _=False,x=n:self.set_bpr(x),shortcut,checkable=True); a.setChecked(n==self.settings['bytes_per_row']); a.setToolTip(f'{n} bytes per row'); self.bpr_group.addAction(a); self.bpr_actions[n]=a
        self.canvas_group=QActionGroup(self); self.canvas_group.setExclusive(True); self.canvas_actions={}
        for key,label in (('dark','Dark Canvas'),('light','Light Canvas')):
            a=self._act(label,lambda _=False,k=key:self.set_canvas(k),checkable=True); a.setChecked(self.settings['canvas_scheme']==key); self.canvas_group.addAction(a); self.canvas_actions[key]=a
        self.a_canvas_toggle=self._act('Light / Dark Canvas',self.toggle_canvas_shortcut,checkable=True); self.a_canvas_toggle.setChecked(self.settings['canvas_scheme']=='light')
        self.colour_group=QActionGroup(self); self.colour_group.setExclusive(True); self.colour_actions={}
        for key,label in (('off','Text Colours Off'),('character_classes','Character Classes'),('detected_strings','Detected Strings')):
            a=self._act(label,lambda _=False,k=key:self.set_text_colour_mode(k),checkable=True); a.setChecked(self.settings['text_colour_mode']==key); self.colour_group.addAction(a); self.colour_actions[key]=a
        self.library_actions={}
        for key,label in (('floating','Library — Floating'),('left','Library — Sidebar Left'),('right','Library — Sidebar Right')):
            a=self._act(label,lambda checked=False,k=key:self.set_library_layout(k,checked),checkable=True); self.library_actions[key]=a
        self.drop_behavior_group=QActionGroup(self); self.drop_behavior_group.setExclusive(True); self.drop_behavior_actions={}
        for key,label in (('active','Opens on Active Window'),('new','Opens on New Window')):
            a=self._act(label,lambda _=False,k=key:self.set_drop_behavior(k),checkable=True); a.setChecked(self.settings.get('drop_behavior','active')==key); self.drop_behavior_group.addAction(a); self.drop_behavior_actions[key]=a
        self.a_show_shortcut_toolbar=self._act('Shortcut Toolbar',lambda checked:self.set_toolbar_visibility('shortcuts',checked),checkable=True); self.a_show_shortcut_toolbar.setChecked(bool(self.settings.get('shortcut_toolbar_visible',True)))
        self.a_show_find_bar=self._act('Find Bar',lambda checked:self.set_toolbar_visibility('find',checked),checkable=True); self.a_show_find_bar.setChecked(bool(self.settings.get('find_bar_visible',True)))
        self.a_add_toolbar_shortcuts=self._act('Add More Shortcuts…',self.configure_shortcut_toolbar); self.a_reset_toolbar_shortcuts=self._act('Reset Shortcut Toolbar',self.reset_shortcut_toolbar)
        self.a_docs=self._act('Documentation',self.show_docs,'F1'); self.a_shortcuts=self._act('Keyboard Shortcuts',self.show_shortcuts,'Ctrl+Shift+/'); self.a_github=self._act('GitHub Repository',lambda:QDesktopServices.openUrl(QUrl(GITHUB_URL))); self.a_issue=self._act('Report an Issue',lambda:QDesktopServices.openUrl(QUrl(GITHUB_URL+'/issues'))); self.a_about=self._act(f'About {APP_NAME}',self.show_about)
        for action in (self.a_find,self.a_next,self.a_prev,self.a_find_all): action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)

    def _make_action_menu(self,title,entries):
        menu=QMenu(title,self)
        for entry in entries:
            if entry is None: menu.addSeparator()
            else: menu.addAction(entry)
        return menu


    def _shortcut_toolbar_catalog(self):
        return [
            ('File',[
                ('open',self.a_open),('reload',self.a_reload),('close_file',self.a_close),('file_info',self.a_info),('exit',self.a_exit),
            ]),
            ('Edit',[
                ('select_all',self.a_select_all),('copy_hex',self.a_copy),('copy_compact',self.a_copy_compact),('copy_escaped',self.a_copy_escaped),('copy_ascii',self.a_copy_ascii),('copy_offset',self.a_copy_offset),('copy_offset_bytes',self.a_copy_offset_bytes),('export_selection',self.a_export),
            ]),
            ('Inspect',[
                ('goto',self.a_goto),('selection_inspector',self.a_inspector),('checksums',self.a_checksums),('entropy',self.a_entropy),('strings',self.a_strings),('runs',self.a_runs),('add_bookmark',self.a_add_bookmark),('bookmarks',self.a_bookmarks),
            ]),
            ('Find',[
                ('find',self.a_find),('find_next',self.a_next),('find_previous',self.a_prev),('find_all',self.a_find_all),
            ]),
            ('View',[
                ('status_bar',self.a_status),('shortcut_toolbar',self.a_show_shortcut_toolbar),('find_bar',self.a_show_find_bar),
                ('show_offset',self.a_offset),('show_ascii',self.a_ascii),('column_ids',self.a_columns),
                ('bpr_8',self.bpr_actions[8]),('bpr_16',self.bpr_actions[16]),('bpr_32',self.bpr_actions[32]),('custom_bpr',self.a_custom_bpr),
                ('canvas_toggle',self.a_canvas_toggle),('text_off',self.colour_actions['off']),('text_classes',self.colour_actions['character_classes']),('text_strings',self.colour_actions['detected_strings']),
                ('library',self.a_library),('library_floating',self.library_actions['floating']),('library_left',self.library_actions['left']),('library_right',self.library_actions['right']),
                ('drop_active',self.drop_behavior_actions['active']),('drop_new',self.drop_behavior_actions['new']),('zoom_in',self.a_zoom_in),('zoom_out',self.a_zoom_out),('zoom_reset',self.a_zoom_reset),('display_font',self.a_font),
            ]),
            ('Help',[('documentation',self.a_docs),('keyboard_shortcuts',self.a_shortcuts),('github',self.a_github),('report_issue',self.a_issue),('about',self.a_about)]),
        ]

    def _shortcut_action_map(self): return {action_id:action for _category,rows in self._shortcut_toolbar_catalog() for action_id,action in rows}
    def _refresh_shortcut_toolbar(self):
        if not hasattr(self,'pane'): return
        mapping=self._shortcut_action_map(); raw=self.settings.get('shortcut_toolbar_shortcuts',[]); selected=[]; seen=set(); aliases={'canvas_dark':'canvas_toggle','canvas_light':'canvas_toggle'}
        if isinstance(raw,list):
            for action_id in raw:
                action_id=aliases.get(str(action_id),str(action_id))
                if action_id in mapping and action_id not in seen: selected.append(action_id); seen.add(action_id)
        self.settings['shortcut_toolbar_shortcuts']=selected; self.pane.set_shortcut_actions([mapping[x] for x in selected])
    def configure_shortcut_toolbar(self):
        d=ShortcutToolbarDialog(self._shortcut_toolbar_catalog(),self.settings.get('shortcut_toolbar_shortcuts',[]),self)
        if d.exec()==QDialog.DialogCode.Accepted: self.settings['shortcut_toolbar_shortcuts']=d.selected_ids(); self._refresh_shortcut_toolbar(); self._save()
    def reset_shortcut_toolbar(self): self.settings['shortcut_toolbar_shortcuts']=[]; self._refresh_shortcut_toolbar(); self._save(); self.statusBar().showMessage('Shortcut Toolbar reset.',2500)

    def _make_toolbar_menus(self):
        self.file_menu=self._make_action_menu('File',[self.a_open,self.a_reload,self.a_close,None,self.a_info,self.a_exit])
        self.edit_menu=self._make_action_menu('Edit',[self.a_select_all,None,self.a_copy,self.a_copy_compact,self.a_copy_escaped,self.a_copy_ascii,self.a_copy_offset,self.a_copy_offset_bytes,None,self.a_export])
        self.inspect_menu=self._make_action_menu('Inspect',[self.a_goto,self.a_inspector,self.a_checksums,self.a_entropy,self.a_strings,self.a_runs,None,self.a_add_bookmark,self.a_bookmarks])
        self.view_menu=QMenu('View',self); self.view_menu.addAction(self.a_status)
        toolbars=self.view_menu.addMenu('Toolbars'); toolbars.addAction(self.a_show_shortcut_toolbar); toolbars.addAction(self.a_show_find_bar); toolbars.addSeparator(); toolbars.addAction(self.a_add_toolbar_shortcuts); toolbars.addAction(self.a_reset_toolbar_shortcuts)
        self.view_menu.addSeparator(); self.view_menu.addAction(self.a_offset); self.view_menu.addAction(self.a_ascii); self.view_menu.addAction(self.a_columns); self.view_menu.addSeparator()
        self.offset_display_menu=self.view_menu.addMenu('Offset Display'); [self.offset_display_menu.addAction(self.offset_mode_actions[k]) for k in ('hex','decimal','both')]
        bpr=self.view_menu.addMenu('Bytes per Row'); [bpr.addAction(self.bpr_actions[n]) for n in (8,16,32)]; bpr.addSeparator(); bpr.addAction(self.a_custom_bpr)
        self.view_menu.addSeparator(); canvas=self.view_menu.addMenu('Canvas'); [canvas.addAction(self.canvas_actions[k]) for k in ('dark','light')]
        colours=self.view_menu.addMenu('Text Colours'); colours.addAction(self.colour_actions['off']); colours.addSeparator(); colours.addAction(self.colour_actions['character_classes']); colours.addAction(self.colour_actions['detected_strings'])
        self.view_menu.addSeparator(); library=self.view_menu.addMenu('Byte Library'); library.addAction(self.a_library); library.addSeparator(); library.addAction(self.library_actions['floating']); library.addSeparator(); library.addAction(self.library_actions['left']); library.addAction(self.library_actions['right'])
        drag_drop=self.view_menu.addMenu('File Drag and Drop'); drag_drop.addAction(self.drop_behavior_actions['active']); drag_drop.addAction(self.drop_behavior_actions['new'])
        self.view_menu.addSeparator(); self.view_menu.addAction(self.a_zoom_in); self.view_menu.addAction(self.a_zoom_out); self.view_menu.addAction(self.a_zoom_reset); self.view_menu.addSeparator(); self.view_menu.addAction(self.a_font)
        self.help_menu=QMenu('Help',self); self.help_menu.addAction(self.a_docs); self.help_menu.addAction(self.a_shortcuts); self.help_menu.addSeparator(); self.help_menu.addAction(self.a_github); self.help_menu.addAction(self.a_issue); self.help_menu.addSeparator(); self.help_menu.addAction(self.a_about)
        self.offset_display_menu.setEnabled(self.a_offset.isChecked())

    def _make_status(self):
        sb=self.statusBar(); self.sig_label=QLabel('No file'); self.pos_label=QLabel('Offset —'); self.size_label=QLabel(''); self.ro_label=QLabel('READ ONLY'); self.ro_label.setStyleSheet('font-weight: 700;'); sb.addWidget(self.sig_label,1); sb.addPermanentWidget(self.pos_label); sb.addPermanentWidget(self.size_label); sb.addPermanentWidget(self.ro_label)

    def _make_dialogs(self):
        self.goto_d=GoToDialog(self); self.goto_d.requested.connect(self.go_to)
        self.library_d=ByteLibraryDialog(self); self.library_d.findRequested.connect(self.find_library_pattern); self.library_d.findAllRequested.connect(self.find_library_all); self.library_d.closed.connect(self._library_dialog_closed)
        self.library_side=ByteLibraryWidget(self); self.library_side.findRequested.connect(self.find_library_pattern); self.library_side.findAllRequested.connect(self.find_library_all)
        self.info_d=FileInfoDialog(self); self.inspector_d=SelectionInspectorDialog(self)
        self.findall_d=OffsetResultsDialog(f'Find All — {APP_NAME}',self); self.findall_d.jumpRequested.connect(self.go_to); self.strings_d=OffsetResultsDialog(f'Strings Finder — {APP_NAME}',self); self.strings_d.jumpRequested.connect(self.go_to); self.runs_d=OffsetResultsDialog(f'Repeated Byte Runs — {APP_NAME}',self); self.runs_d.jumpRequested.connect(self.go_to)
        self.bookmarks_d=BookmarkDialog(self); self.bookmarks_d.jumpRequested.connect(self.go_to); self.bookmarks_d.removeRequested.connect(self.remove_bookmark); self.bookmarks_d.clearRequested.connect(self.clear_bookmarks); self.checksum_d=SimpleReportDialog(f'Selected Range Checksums — {APP_NAME}',self); self.entropy_d=SimpleReportDialog(f'Entropy — {APP_NAME}',self)
        docs=(PROGRAM_ROOT/'docs'/'README.md').read_text(encoding='utf-8'); self.docs_d=TextDialog(f'Documentation — {APP_NAME}',docs,self)
        shortcut_groups=[
            ('File',[('Open file','Ctrl+O'),('File Information / Metadata','Alt+Return'),('Reload','F5'),('Close file','Ctrl+W'),('Exit','Ctrl+Q')]),
            ('Find',[('Focus Find bar','Ctrl+F'),('Find next','Enter'),('Find previous','Shift+Enter'),('Go to offset','Ctrl+G'),('Find all current search','Ctrl+Shift+F')]),
            ('View',[('Show Offset','Ctrl+Alt+O'),('Show ASCII','Ctrl+Alt+A'),('Show Column Identifiers','Ctrl+Alt+I'),('8 bytes per row','Ctrl+1'),('16 bytes per row','Ctrl+2'),('32 bytes per row','Ctrl+3'),('Increase font size','Ctrl++'),('Decrease font size','Ctrl+-'),('Reset font size','Ctrl+0')]),
            ('Bookmarks',[('Add bookmark','Ctrl+B'),('Manage bookmarks','Ctrl+Shift+B')]),
            ('Edit / Inspect',[('Select All','Ctrl+A'),('Copy Hex','Ctrl+C'),('Copy Offset + Bytes','Ctrl+Shift+C'),('Export Selection','Ctrl+Shift+E'),('Selection Inspector','Ctrl+I'),('Entropy','Ctrl+E'),('Strings Finder','Ctrl+Alt+S'),('Byte Library','Ctrl+L')]),
            ('Help',[('Documentation','F1'),('Keyboard Shortcuts','Ctrl+Shift+/')]),
        ]; self.shortcuts_d=KeyboardShortcutsDialog(shortcut_groups,self); self.about_d=AboutDialog(ICON_PATH,config_path(),self)

    def _make_central(self):
        self.pane=FilePane(self,self.view,self); self._refresh_shortcut_toolbar()
        self._content_widget=QWidget(self); cl=QVBoxLayout(self._content_widget); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0); cl.addWidget(self.pane,1)
        self._library_sidebar=QFrame(self); self._library_sidebar.setFrameShape(QFrame.Shape.StyledPanel); ll=QVBoxLayout(self._library_sidebar); ll.setContentsMargins(0,0,0,0); ll.setSpacing(0); hdr=QWidget(self._library_sidebar); hl=QHBoxLayout(hdr); hl.setContentsMargins(5,2,3,2); title=QLabel('Byte Library',hdr); title.setStyleSheet('font-weight: 600;'); self._library_close=QToolButton(hdr); self._library_close.setText('×'); self._library_close.setToolTip('Close Byte Library'); self._library_close.setAutoRaise(True); self._library_close.setFixedSize(26,26); self._library_close.clicked.connect(lambda:self.set_library_visible(False)); hl.addWidget(title,1); hl.addWidget(self._library_close,0); ll.addWidget(hdr,0); ll.addWidget(self.library_side,1); self._library_sidebar.setMinimumWidth(240); self._library_sidebar.setMaximumWidth(420)
        self._outer_splitter=QSplitter(Qt.Orientation.Horizontal,self); self._outer_splitter.setChildrenCollapsible(False); self._outer_splitter.addWidget(self._content_widget); self._outer_splitter.addWidget(self._library_sidebar); self._outer_splitter.setStretchFactor(0,1); self._outer_splitter.setStretchFactor(1,0); self._outer_splitter.splitterMoved.connect(self._library_splitter_moved); self.setCentralWidget(self._outer_splitter)
        self._apply_toolbar_visibility(save=False); self._apply_library_layout(save=False)

    def _show_toolbar_context(self,global_pos):
        menu=QMenu(self); menu.addAction(self.a_show_shortcut_toolbar); menu.addAction(self.a_show_find_bar); menu.addSeparator(); menu.addAction(self.a_add_toolbar_shortcuts); menu.addAction(self.a_reset_toolbar_shortcuts); menu.exec(global_pos)

    def _library_splitter_moved(self,*_):
        if self.settings.get('library_layout','floating') in ('left','right') and self._library_sidebar.isVisible():
            self._library_sidebar_width=max(240,min(420,self._library_sidebar.width())); self.settings['library_sidebar_width']=self._library_sidebar_width
            if not self._restoring_ui: self._save()

    def _save(self):
        font=self.view.display_font(); self.settings.update({'bytes_per_row':self.view.bytes_per_row,'show_ascii':self.view.show_ascii,'show_offset':self.view.show_offset,'show_column_identifiers':self.view.show_column_identifiers,'font_family':font.family(),'font_size':self.view.font_size(),'font_weight':int(font.weight()),'font_italic':font.italic(),'canvas_scheme':self.view.canvas_scheme,'text_colour_mode':self.view.text_colour_mode,'offset_mode':self.view.offset_mode,'status_bar_visible':not self.statusBar().isHidden(),'shortcut_toolbar_visible':self.pane.shortcut_toolbar.isVisible(),'find_bar_visible':self.pane.search_bar.isVisible()})
        try: self.settings['window_geometry']=bytes(self.saveGeometry().toHex()).decode('ascii')
        except Exception: pass
        save_settings(self.settings)

    def _restore_ui(self):
        geom=self.settings.get('window_geometry','')
        try:
            if geom: self.restoreGeometry(QByteArray.fromHex(QByteArray(geom.encode('ascii'))))
        except Exception: pass
        status=bool(self.settings.get('status_bar_visible',True)); self.statusBar().setVisible(status); self.a_status.blockSignals(True); self.a_status.setChecked(status); self.a_status.blockSignals(False); self._apply_toolbar_visibility(save=False); self._apply_library_layout(save=False)

    def toggle_status_bar(self,checked):
        visible=bool(checked); self.statusBar().setVisible(visible); self.settings['status_bar_visible']=visible; self.a_status.blockSignals(True); self.a_status.setChecked(visible); self.a_status.blockSignals(False)
        if not self._restoring_ui: self._save()
    def set_toolbar_visibility(self,kind,visible):
        visible=bool(visible)
        if kind=='shortcuts': self.settings['shortcut_toolbar_visible']=visible
        elif kind=='find': self.settings['find_bar_visible']=visible
        else: return
        self._apply_toolbar_visibility(save=True)
    def _apply_toolbar_visibility(self,save=False):
        sv=bool(self.settings.get('shortcut_toolbar_visible',True)); fv=bool(self.settings.get('find_bar_visible',True)); self.pane.main_toolbar.show(); self.pane.shortcut_toolbar.setVisible(sv); self.pane.search_bar.setVisible(fv)
        for action,value in ((self.a_show_shortcut_toolbar,sv),(self.a_show_find_bar,fv)): action.blockSignals(True); action.setChecked(value); action.blockSignals(False)
        if save and not self._restoring_ui: self._save()

    def _sync_library_actions(self):
        layout=self.settings.get('library_layout','floating'); visible=bool(self.settings.get('library_visible',False)); self.a_library.blockSignals(True); self.a_library.setChecked(visible); self.a_library.setText('Byte Library…' if layout=='floating' else 'Byte Library'); self.a_library.blockSignals(False)
        for key,a in self.library_actions.items(): a.blockSignals(True); a.setChecked(visible and key==layout); a.blockSignals(False)
    def set_library_visible(self,visible): self.settings['library_visible']=bool(visible); self._apply_library_layout(save=True)
    def set_library_layout(self,layout,checked=False):
        if layout not in ('floating','left','right'): return
        current=self.settings.get('library_layout','floating'); visible=bool(self.settings.get('library_visible',False))
        if layout==current and visible: self.settings['library_visible']=False
        else: self.settings['library_layout']=layout; self.settings['library_visible']=True
        self._apply_library_layout(save=True)
    def _apply_library_layout(self,save=False):
        layout=self.settings.get('library_layout','floating'); visible=bool(self.settings.get('library_visible',False))
        if not visible: self._library_sidebar.hide(); self.library_d.hide()
        elif layout=='floating': self._library_sidebar.hide(); self.library_d.show(); self.library_d.raise_(); self.library_d.activateWindow()
        else:
            self.library_d.hide(); self._library_sidebar.show(); width=max(240,min(420,self._library_sidebar_width)); total=max(self.width(),width+500)
            if layout=='left': self._outer_splitter.insertWidget(0,self._library_sidebar); self._outer_splitter.insertWidget(1,self._content_widget); self._outer_splitter.setSizes([width,max(400,total-width)])
            else: self._outer_splitter.insertWidget(0,self._content_widget); self._outer_splitter.insertWidget(1,self._library_sidebar); self._outer_splitter.setSizes([max(400,total-width),width])
        self._sync_library_actions()
        if save and not self._restoring_ui: self._save()
    def _library_dialog_closed(self):
        if self.settings.get('library_layout','floating')=='floating' and self.settings.get('library_visible',False): self.settings['library_visible']=False; self._sync_library_actions(); self._save()

    def focus_find(self):
        if not self.pane.search_bar.isVisible(): self.set_toolbar_visibility('find',True)
        self.pane.search_bar.focus_entry()
    def _pattern_for(self,mode,text):
        try: return encode_text_pattern(text) if mode=='text' else parse_hex_pattern(text)
        except ValueError as e: QMessageBox.warning(self,'Invalid Search',str(e)); return b''
    def search_from_bar(self,mode,text,direction):
        pattern=self._pattern_for(mode,text)
        if not pattern: return
        self._last_pattern=bytes(pattern); a,b=self.view.selection_range(); start=b if direction=='forward' else a; self._launch_search(self._last_pattern,direction,start)
    def find_all_from_bar(self,mode,text):
        pattern=self._pattern_for(mode,text)
        if not pattern: return
        self._last_pattern=bytes(pattern); self._launch_analysis('find_all',{'pattern':self._last_pattern,'start':0})

    def open_dialog(self):
        path,_=QFileDialog.getOpenFileName(self,'Open Binary / File')
        if path: self.open_path(path)
    def open_path(self,path):
        self._cancel_search(); self._cancel_analysis()
        try: new=ByteSource(path)
        except Exception as e: QMessageBox.warning(self,'Cannot Open File',str(e)); return
        old=self.source; self.source=new; self.pane.set_source(new); self._external_warned=False
        if old: old.close()
        self._bookmark_fingerprint=source_fingerprint(new); self._last_pattern=None; self._refresh_bookmarks(); sig=identify_source(new); self.sig_label.setText(f'Likely: {sig.name}' if sig else 'Likely type: unknown'); self.size_label.setText(human_size(new.size)); self.setWindowTitle(f'{new.path.name} — {APP_NAME}')
        if self.info_d.isVisible(): self.info_d.set_source(new)
        self._update_enabled(); self._update_position()
    def reload_file(self):
        if self.source: self.open_path(str(self.source.path))
    def close_file(self):
        self._cancel_search(); self._cancel_analysis()
        if self.source: self.source.close(); self.source=None
        self.pane.set_source(None); self.info_d.set_source(None); self._bookmark_fingerprint=None; self.bookmarks_d.set_bookmarks([]); self.sig_label.setText('No file'); self.size_label.clear(); self.pos_label.setText('Offset —'); self.setWindowTitle(APP_NAME); self._update_enabled()
    def _update_enabled(self):
        has=self.source is not None
        for a in (self.a_select_all,self.a_copy,self.a_copy_compact,self.a_copy_escaped,self.a_copy_ascii,self.a_reload,self.a_close,self.a_info,self.a_find,self.a_next,self.a_prev,self.a_find_all,self.a_goto,self.a_strings,self.a_runs,self.a_add_bookmark,self.a_bookmarks,self.a_export,self.a_inspector,self.a_checksums,self.a_entropy,self.a_copy_offset,self.a_copy_offset_bytes): a.setEnabled(has)
    def show_info(self):
        if self.source: self.info_d.set_source(self.source); self.info_d.show(); self.info_d.raise_(); self.info_d.activateWindow()
    def show_goto(self): self.goto_d.show(); self.goto_d.raise_(); self.goto_d.activateWindow()
    def show_library(self,checked=False): self.set_library_visible(bool(checked))
    def find_library_pattern(self,pattern):
        if self.source: self._last_pattern=bytes(pattern); self._launch_search(self._last_pattern,'forward',0)
    def find_library_all(self,pattern):
        if self.source: self._last_pattern=bytes(pattern); self._launch_analysis('find_all',{'pattern':bytes(pattern),'start':0})
    def show_docs(self): self.docs_d.show(); self.docs_d.raise_(); self.docs_d.activateWindow()
    def show_shortcuts(self): self.shortcuts_d.show(); self.shortcuts_d.raise_(); self.shortcuts_d.activateWindow()
    def show_about(self): self.about_d.show(); self.about_d.raise_(); self.about_d.activateWindow()
    def _all_views(self): return [self.view]
    def set_drop_behavior(self,mode):
        if mode not in ('active','new'): return
        self.settings['drop_behavior']=mode
        for key,a in self.drop_behavior_actions.items(): a.blockSignals(True); a.setChecked(key==mode); a.blockSignals(False)
        self._save()
    def set_bpr(self,n):
        n=max(1,min(64,int(n))); self.view.set_bytes_per_row(n)
        for value,a in self.bpr_actions.items(): a.blockSignals(True); a.setChecked(value==n); a.blockSignals(False)
        self._save()
    def custom_bpr(self):
        value,ok=QInputDialog.getInt(self,'Custom Bytes per Row','Bytes per row:',self.view.bytes_per_row,1,64,1)
        if ok: self.set_bpr(value)
    def toggle_ascii(self,checked): self.view.set_show_ascii(checked); self._save()
    def toggle_offset(self,checked): self.view.set_show_offset(checked); self.offset_display_menu.setEnabled(bool(checked)); self._save()
    def toggle_column_identifiers(self,checked): self.view.set_show_column_identifiers(checked); self._save()
    def set_offset_mode(self,mode):
        self.view.set_offset_mode(mode); self.settings['offset_mode']=mode
        for key,a in self.offset_mode_actions.items(): a.blockSignals(True); a.setChecked(key==mode); a.blockSignals(False)
        for d in (self.findall_d,self.strings_d,self.runs_d): d.set_offset_mode(mode)
        self._refresh_bookmarks(); self._update_position(); self._save()
    def set_canvas(self,scheme):
        self.view.set_canvas_scheme(scheme); self.settings['canvas_scheme']=scheme
        for key,a in self.canvas_actions.items(): a.blockSignals(True); a.setChecked(key==scheme); a.blockSignals(False)
        self.a_canvas_toggle.blockSignals(True); self.a_canvas_toggle.setChecked(scheme=='light'); self.a_canvas_toggle.blockSignals(False); self._save()
    def toggle_canvas_shortcut(self,checked): self.set_canvas('light' if checked else 'dark')
    def set_text_colour_mode(self,mode):
        self.view.set_text_colour_mode(mode); self.settings['text_colour_mode']=mode
        for key,a in self.colour_actions.items(): a.blockSignals(True); a.setChecked(key==mode); a.blockSignals(False)
        self._save()
    def zoom(self,d): self.view.set_font_size(self.view.font_size()+d); self._save()
    def zoom_reset(self): self.view.set_font_size(11); self._save()
    def choose_font(self):
        dialog=QFontDialog(self.view.display_font(),self); dialog.setWindowTitle(f'Display Font — {APP_NAME}')
        try: dialog.setOption(QFontDialog.FontDialogOption.MonospacedFonts,True)
        except Exception: pass
        if dialog.exec()==QDialog.DialogCode.Accepted: self.view.set_display_font(dialog.selectedFont()); self._save()
    def go_to(self,offset):
        if not self.source or self.source.size<=0: return
        if offset>=self.source.size: QMessageBox.information(self,'Offset Outside File',f'Maximum offset is 0x{self.source.size-1:X}.'); return
        self.view.set_cursor(offset)
    def _status_offset(self,offset):
        mode=self.view.offset_mode
        if mode=='decimal': return str(int(offset))
        if mode=='both': return f'0x{int(offset):X} ({int(offset)})'
        return f'0x{int(offset):X}'
    def show_selection_inspector(self): self._update_inspector(); self.inspector_d.show(); self.inspector_d.raise_(); self.inspector_d.activateWindow()
    def _update_inspector_if_visible(self):
        if self.inspector_d.isVisible(): self._update_inspector()
    def _update_inspector(self):
        if not self.source: return
        a,b=self.view.selection_range(); length=b-a; data=self.source.read(a,min(length,256)); self.inspector_d.set_values(self._status_offset(a),selection_interpretation(data,length))
    def find_all_current(self):
        if not self.source: return
        mode,text=self.pane.search_bar.state(); pattern=self._pattern_for(mode,text)
        if not pattern: self.focus_find(); return
        self._last_pattern=bytes(pattern); self._launch_analysis('find_all',{'pattern':self._last_pattern,'start':0})
    def show_strings(self): self._launch_analysis('strings',{'minimum':4})
    def show_repeated_runs(self): self._launch_analysis('runs',{'minimum':16})
    def show_selection_checksums(self):
        if not self.source: return
        a,b=self.view.selection_range(); self._launch_analysis('checksums',{'start':a,'length':b-a})
    def show_entropy(self):
        if not self.source: return
        a,b=self.view.selection_range(); length=b-a
        if length<=1: a=0; length=self.source.size
        self._launch_analysis('entropy',{'start':a,'length':length})
    def _launch_analysis(self,kind,args):
        if not self.source or self._analysis_thread: return
        self._analysis_context={'kind':kind,**dict(args)}; self.statusBar().showMessage('Analysing…'); t=QThread(self); worker=AnalysisWorker(str(self.source.path),kind,args); worker.moveToThread(t); t.started.connect(worker.run); worker.done.connect(self._analysis_done); worker.failed.connect(self._analysis_failed); worker.done.connect(t.quit); worker.failed.connect(t.quit); t.finished.connect(lambda:self._analysis_clear(t,worker)); self._analysis_thread=t; self._analysis_worker=worker; t.start()
    def _analysis_done(self,kind,result):
        self.statusBar().clearMessage()
        if kind=='find_all':
            rows=[(int(off),'Match') for off in (result or [])]; self.findall_d.set_offset_mode(self.view.offset_mode); self.findall_d.set_rows(rows,f"{len(rows):,} match{'es' if len(rows)!=1 else ''} (maximum 10,000)"); self.findall_d.show(); self.findall_d.raise_()
        elif kind=='strings':
            rows=[]
            for off,total_length,data in (result or []):
                text=data.decode('ascii','replace'); preview=text if len(text)<=120 else text[:117]+'…'; preview += '…' if total_length>len(data) else ''; rows.append((int(off),f'{total_length:,} bytes  {preview}'))
            self.strings_d.set_offset_mode(self.view.offset_mode); self.strings_d.set_rows(rows,f"{len(rows):,} printable ASCII string{'s' if len(rows)!=1 else ''} (minimum 4 bytes; maximum 10,000)"); self.strings_d.show(); self.strings_d.raise_()
        elif kind=='runs':
            rows=[(int(off),f'{length:,} × {value:02X}') for off,value,length in (result or [])]; self.runs_d.set_offset_mode(self.view.offset_mode); self.runs_d.set_rows(rows,f"{len(rows):,} repeated-byte run{'s' if len(rows)!=1 else ''} (minimum 16 bytes)"); self.runs_d.show(); self.runs_d.raise_()
        elif kind=='checksums':
            if result is None: return
            ctx=self._analysis_context; a=int(ctx.get('start',0)); length=int(ctx.get('length',0)); text=f'Range: {self._status_offset(a)} — {self._status_offset(max(a,a+length-1))}\nLength: {length:,} bytes\n\n'+'\n'.join(f'{k}: {v}' for k,v in result.items()); self.checksum_d.set_text(text); self.checksum_d.show(); self.checksum_d.raise_()
        elif kind=='entropy':
            if result is None: return
            ctx=self._analysis_context; a=ctx.get('start',0); length=ctx.get('length',0); value=float(result); text=f'Range start: {self._status_offset(a)}\nLength: {length:,} bytes\nEntropy: {value:.4f} bits/byte\n\n{entropy_description(value)}\n\nHigh entropy does not prove encryption; compressed data can look similar.'; self.entropy_d.set_text(text); self.entropy_d.show(); self.entropy_d.raise_()
    def _analysis_failed(self,kind,msg): self.statusBar().showMessage('Analysis failed',3000); QMessageBox.warning(self,'Analysis Failed',msg)
    def _analysis_clear(self,t,w):
        if self._analysis_thread is t: self._analysis_thread=None; self._analysis_worker=None
        w.deleteLater(); t.deleteLater()
    def _cancel_analysis(self):
        t=self._analysis_thread; w=getattr(self,'_analysis_worker',None)
        if not t: return
        if w:
            try: w.done.disconnect(self._analysis_done)
            except (TypeError,RuntimeError): pass
            try: w.failed.disconnect(self._analysis_failed)
            except (TypeError,RuntimeError): pass
        t.requestInterruption(); t.quit(); t.wait(3000)
        if self._analysis_thread is t: self._analysis_thread=None; self._analysis_worker=None
    def add_bookmark(self):
        if not self.source or self.source.size==0 or self._bookmark_fingerprint is None: return
        label,ok=QInputDialog.getText(self,'Add Bookmark',f'Label for {self._status_offset(self.view.cursor_offset)} (optional):')
        if not ok: return
        self.bookmark_store.add(self._bookmark_fingerprint,self.source.size,self.view.cursor_offset,label); self._refresh_bookmarks(); self.statusBar().showMessage('Bookmark saved without storing the source path',3000)
    def _refresh_bookmarks(self):
        if not self.source or self._bookmark_fingerprint is None: self.bookmarks_d.set_bookmarks([]); return
        self.bookmarks_d.set_offset_mode(self.view.offset_mode); self.bookmarks_d.set_bookmarks(self.bookmark_store.list(self._bookmark_fingerprint,self.source.size))
    def show_bookmarks(self): self._refresh_bookmarks(); self.bookmarks_d.show(); self.bookmarks_d.raise_(); self.bookmarks_d.activateWindow()
    def remove_bookmark(self,offset):
        if self.source and self._bookmark_fingerprint is not None: self.bookmark_store.remove(self._bookmark_fingerprint,self.source.size,int(offset)); self._refresh_bookmarks()
    def clear_bookmarks(self):
        if self._bookmark_fingerprint is not None: self.bookmark_store.clear(self._bookmark_fingerprint); self._refresh_bookmarks()
    def export_selection(self):
        if not self.source: return
        start,end=self.view.selection_range(); length=end-start
        if length<=0: return
        target,_=QFileDialog.getSaveFileName(self,'Export Selected Bytes')
        if not target: return
        progress=QProgressDialog('Exporting selected bytes…','Cancel',0,1000,self); progress.setWindowModality(Qt.WindowModality.WindowModal); progress.setMinimumDuration(300)
        def on_progress(done,total): progress.setValue(1000 if total==0 else int((done/total)*1000)); QApplication.processEvents()
        try: export_range(self.source,start,length,target,progress=on_progress,cancelled=progress.wasCanceled); progress.setValue(1000); self.statusBar().showMessage(f'Exported {length:,} bytes',4000)
        except InterruptedError: self.statusBar().showMessage('Export cancelled',2500)
        except Exception as exc: QMessageBox.warning(self,'Export Failed',str(exc))
    def _launch_search(self,pattern,direction,start):
        if not self.source or self._search_thread: return
        self.statusBar().showMessage('Searching…'); t=QThread(self); worker=SearchWorker(str(self.source.path),bytes(pattern),int(start),direction); worker.moveToThread(t); t.started.connect(worker.run); worker.done.connect(self._search_done); worker.failed.connect(self._search_failed); worker.done.connect(t.quit); worker.failed.connect(t.quit); t.finished.connect(lambda:self._search_clear(t,worker)); self._search_thread=t; self._search_worker=worker; t.start()
    def repeat_find(self,direction):
        mode,text=self.pane.search_bar.state(); pattern=self._pattern_for(mode,text)
        if pattern: self._last_pattern=bytes(pattern)
        if not self._last_pattern: self.focus_find(); return
        a,b=self.view.selection_range(); start=b if direction=='forward' else a; self._launch_search(self._last_pattern,direction,start)
    def _search_done(self,result,length):
        if result is None: self.statusBar().showMessage('Pattern not found',3000)
        else: self.view.set_selection(int(result),int(length)); self.statusBar().showMessage(f'Match at 0x{int(result):X}',3000)
    def _search_failed(self,msg): self.statusBar().showMessage('Search failed',3000); QMessageBox.warning(self,'Search Failed',msg)
    def _search_clear(self,t,w):
        if self._search_thread is t: self._search_thread=None; self._search_worker=None
        w.deleteLater(); t.deleteLater()
    def _cancel_search(self):
        t=self._search_thread; w=getattr(self,'_search_worker',None)
        if not t: return
        if w:
            try: w.done.disconnect(self._search_done)
            except (TypeError,RuntimeError): pass
            try: w.failed.disconnect(self._search_failed)
            except (TypeError,RuntimeError): pass
        t.requestInterruption(); t.quit(); t.wait(3000)
        if self._search_thread is t: self._search_thread=None; self._search_worker=None
    def _update_position(self,*_):
        if not self.source: self.sig_label.setText('No file'); self.size_label.clear(); self.pos_label.setText('Offset —'); return
        a,b=self.view.selection_range(); count=max(0,b-a); self.pos_label.setText(f'Offset {self._status_offset(self.view.cursor_offset)} | Selected {count:,} byte{"s" if count!=1 else ""}'); self._update_inspector_if_visible()
    def _check_external(self):
        if not self.source: return
        if self.source.changed_on_disk(): self.sig_label.setText('File changed on disk — Reload recommended'); self._external_warned=True
        elif self._external_warned:
            sig=identify_source(self.source); self.sig_label.setText(f'Likely: {sig.name}' if sig else 'Likely type: unknown'); self._external_warned=False
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and len(event.mimeData().urls())==1 and event.mimeData().urls()[0].isLocalFile(): event.acceptProposedAction()
    def dropEvent(self,event):
        path=event.mimeData().urls()[0].toLocalFile(); mods=event.modifiers(); mode=self.settings.get('drop_behavior','active')
        if mods & Qt.KeyboardModifier.ShiftModifier: mode='new' if mode=='active' else 'active'
        if mode=='new': self._open_new_window(path)
        else: self.open_path(path)
        event.acceptProposedAction()
    def closeEvent(self,event):
        self._save(); self._cancel_search(); self._cancel_analysis(); self.info_d.shutdown()
        if self.source: self.source.close()
        try: WINDOWS.remove(self)
        except ValueError: pass
        super().closeEvent(event)


def main(argv=None):
    args=list(argv or []); app=QApplication([sys.argv[0],*args]); app.setApplicationName(APP_NAME); app.setApplicationDisplayName(APP_NAME); app.setApplicationVersion(APP_VERSION); app.setOrganizationName(ORGANISATION); app.setOrganizationDomain(ORGANISATION_DOMAIN); app.setDesktopFileName(APPSTREAM_ID)
    if ICON_PATH.exists(): app.setWindowIcon(QIcon(str(ICON_PATH)))
    initial=next((x for x in args if not x.startswith('-')),None); w=BeespectorWindow(initial); w.show(); return app.exec()
