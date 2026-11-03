from __future__ import annotations
import datetime, html, json, mimetypes, os, stat
from pathlib import Path
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from PyQt6.QtGui import QFontDatabase, QPixmap, QKeySequence, QIcon
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,QPushButton,
    QComboBox,QListWidget,QListWidgetItem,QPlainTextEdit,QWidget,QDialogButtonBox,QTableWidget,
    QTableWidgetItem,QHeaderView,QAbstractItemView,QSpinBox,QTabWidget,QTreeWidget,QTreeWidgetItem,QFileDialog,QApplication,QSplitter)
from . import APP_NAME, APP_VERSION
from .byte_source import ByteSource
from .formatting import human_size, as_hex
from .signatures import library_rows
from .metadata import metadata_snapshot

GITHUB_URL="https://github.com/brunonlinespace/beespector"

class GoToDialog(QDialog):
    requested=pyqtSignal(int)
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle(f"Go to Offset — {APP_NAME}"); self.setModal(False); self.setMinimumWidth(360)
        lay=QVBoxLayout(self); self.edit=QLineEdit(); self.edit.setPlaceholderText("Hex 0x1A20 or decimal 6688"); lay.addWidget(self.edit)
        self.error=QLabel(); lay.addWidget(self.error); box=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok); lay.addWidget(box); box.rejected.connect(self.hide); box.accepted.connect(self._accept); self.edit.returnPressed.connect(self._accept)
    def _accept(self):
        t=self.edit.text().strip().replace("_","")
        try: value=int(t,16) if t.lower().startswith("0x") else int(t,10)
        except ValueError: self.error.setText("Enter an offset such as 0x1A20 or 6688."); return
        if value<0: self.error.setText("Offset cannot be negative."); return
        self.error.clear(); self.requested.emit(value); self.hide()

class ByteLibraryWidget(QWidget):
    findRequested=pyqtSignal(bytes)
    findAllRequested=pyqtSignal(bytes)
    def __init__(self,parent=None):
        super().__init__(parent)
        lay=QVBoxLayout(self); lay.setContentsMargins(6,6,6,6)
        top=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText("Search signatures and byte references…"); self.category=QComboBox(); top.addWidget(self.search,1); top.addWidget(self.category); lay.addLayout(top)
        self.list=QListWidget(); self.details=QPlainTextEdit(); self.details.setReadOnly(True); self.details.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)); self.body_splitter=QSplitter(Qt.Orientation.Vertical,self); self.body_splitter.setChildrenCollapsible(False); self.body_splitter.setHandleWidth(5); self.body_splitter.addWidget(self.list); self.body_splitter.addWidget(self.details); self.body_splitter.setStretchFactor(0,3); self.body_splitter.setStretchFactor(1,2); self.body_splitter.setSizes([300,180]); lay.addWidget(self.body_splitter,1)
        buttons=QHBoxLayout(); buttons.addStretch(1); self.copy=QPushButton("Copy Hex"); self.find=QPushButton("Find in File"); self.find_all=QPushButton("Find All"); buttons.addWidget(self.copy); buttons.addWidget(self.find); buttons.addWidget(self.find_all); lay.addLayout(buttons)
        self.rows=library_rows(); cats=["All"]+sorted({r[0] for r in self.rows}); self.category.addItems(cats)
        self.search.textChanged.connect(self._populate); self.category.currentTextChanged.connect(self._populate); self.list.currentItemChanged.connect(self._show); self.copy.clicked.connect(self._copy); self.find.clicked.connect(self._find); self.find_all.clicked.connect(self._find_all); self._populate()
    def _populate(self,*_):
        q=self.search.text().casefold(); cat=self.category.currentText(); self.list.clear()
        for category,name,pattern,desc,offsets,extensions,auto_detect in self.rows:
            if cat!="All" and category!=cat: continue
            hay=f"{category} {name} {desc} {as_hex(pattern)} {offsets} {extensions}".casefold()
            if q and q not in hay: continue
            item=QListWidgetItem(f"{name}  —  {as_hex(pattern)}")
            item.setData(Qt.ItemDataRole.UserRole,(category,name,pattern,desc,offsets,extensions,auto_detect))
            self.list.addItem(item)
        if self.list.count(): self.list.setCurrentRow(0)
    def _current(self):
        i=self.list.currentItem(); return i.data(Qt.ItemDataRole.UserRole) if i else None
    def _show(self,*_):
        row=self._current()
        if not row: self.details.clear(); return
        category,name,pattern,desc,offsets,extensions,auto_detect=row
        detection = "Automatic" if auto_detect else "Library/reference only"
        self.details.setPlainText(
            f"{name}\n\nCategory: {category}\nBytes: {as_hex(pattern)}\nOffset: {offsets}\n"
            f"Known extensions: {extensions}\nDetection: {detection}\n\n{desc}"
        )
    def _copy(self):
        from PyQt6.QtWidgets import QApplication
        row=self._current()
        if row: QApplication.clipboard().setText(as_hex(row[2]))
    def _find(self):
        row=self._current()
        if row: self.findRequested.emit(row[2])
    def _find_all(self):
        row=self._current()
        if row: self.findAllRequested.emit(row[2])

class ByteLibraryDialog(QDialog):
    findRequested=pyqtSignal(bytes)
    findAllRequested=pyqtSignal(bytes)
    closed=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle(f"Byte Library — {APP_NAME}"); self.setModal(False); self.resize(720,540)
        lay=QVBoxLayout(self); self.library=ByteLibraryWidget(self); lay.addWidget(self.library); self.library.findRequested.connect(self.findRequested); self.library.findAllRequested.connect(self.findAllRequested)
    def closeEvent(self,event):
        super().closeEvent(event); self.closed.emit()

class HashWorker(QObject):
    done=pyqtSignal(object); failed=pyqtSignal(str)
    def __init__(self,path): super().__init__(); self.path=path
    def run(self):
        try:
            with ByteSource(self.path) as s: value=s.sha256(cancelled=lambda:QThread.currentThread().isInterruptionRequested())
            self.done.emit(value)
        except Exception as e: self.failed.emit(str(e))

class FileInfoDialog(QDialog):
    """Read-only universal + embedded metadata inspector."""
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle(f"File Information — {APP_NAME}"); self.setModal(False); self.resize(760,560); self._thread=None; self.path=None; self._snapshot={}
        lay=QVBoxLayout(self); self.tabs=QTabWidget(self); lay.addWidget(self.tabs,1)
        self.trees={}
        for title in ("Summary","Filesystem","Embedded Metadata","Integrity"):
            tree=QTreeWidget(self); tree.setColumnCount(2); tree.setHeaderLabels(["Property","Value"]); tree.header().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); tree.header().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); tree.setAlternatingRowColors(True); tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.tabs.addTab(tree,title); self.trees[title]=tree
        integ=self.trees["Integrity"]; self.hash_item=QTreeWidgetItem(["SHA-256","Not calculated"]); integ.addTopLevelItem(self.hash_item)
        row=QHBoxLayout(); self.copy_btn=QPushButton("Copy All",self); self.export_btn=QPushButton("Export JSON…",self); self.hash_btn=QPushButton("Calculate SHA-256",self); close=QPushButton("Close",self); row.addWidget(self.copy_btn); row.addWidget(self.export_btn); row.addStretch(1); row.addWidget(self.hash_btn); row.addWidget(close); lay.addLayout(row)
        self.copy_btn.clicked.connect(self._copy_all); self.export_btn.clicked.connect(self._export_json); self.hash_btn.clicked.connect(self._hash); close.clicked.connect(self.hide)
    def _fill_tree(self,title,rows):
        tree=self.trees[title]; tree.clear()
        for key,value in rows:
            item=QTreeWidgetItem([str(key),str(value)]); item.setToolTip(1,str(value)); tree.addTopLevelItem(item)
    def set_source(self,source: ByteSource | None):
        self._cancel_hash(); self.path=None if source is None else str(source.path); self._snapshot={}
        for title in ("Summary","Filesystem","Embedded Metadata"): self.trees[title].clear()
        self.trees["Integrity"].clear(); self.hash_item=QTreeWidgetItem(["SHA-256","Not calculated"]); self.trees["Integrity"].addTopLevelItem(self.hash_item)
        if source is None:
            self.copy_btn.setEnabled(False); self.export_btn.setEnabled(False); self.hash_btn.setEnabled(False); return
        snap=metadata_snapshot(source)
        # Summary gets the most useful universal fields first.
        summary=[("File",str(source.path)),("Size",f"{source.size:,} bytes ({human_size(source.size)})")]+list(snap.get("Summary",[]))
        self._snapshot={"Summary":summary,"Filesystem":list(snap.get("Filesystem",[])),"Embedded Metadata":list(snap.get("Embedded Metadata",[])),"Integrity":[("SHA-256","Not calculated")]}
        for title in ("Summary","Filesystem","Embedded Metadata"): self._fill_tree(title,self._snapshot[title])
        self.copy_btn.setEnabled(True); self.export_btn.setEnabled(True); self.hash_btn.setEnabled(True)
    def _serialisable(self):
        return {section:{key:value for key,value in rows} for section,rows in self._snapshot.items()}
    def _copy_all(self):
        if not self._snapshot: return
        lines=[]
        for section,rows in self._snapshot.items():
            lines.append(f"[{section}]"); lines.extend(f"{k}: {v}" for k,v in rows); lines.append("")
        QApplication.clipboard().setText("\n".join(lines).rstrip()+"\n")
    def _export_json(self):
        if not self._snapshot: return
        path,_=QFileDialog.getSaveFileName(self,"Export Metadata",filter="JSON files (*.json);;All files (*)")
        if not path: return
        from PyQt6.QtWidgets import QMessageBox
        try:
            if self.path and Path(path).expanduser().resolve()==Path(self.path).resolve():
                QMessageBox.warning(self,"Export Metadata Refused","Choose a separate output file. Beespector Lite will not write metadata over the inspected source."); return
        except OSError:
            pass
        try:
            Path(path).write_text(json.dumps(self._serialisable(),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self,"Export Metadata Failed",str(exc))
    def _hash(self):
        if not self.path or self._thread: return
        self.hash_btn.setEnabled(False); self.hash_item.setText(1,"Calculating…")
        t=QThread(self); w=HashWorker(self.path); w.moveToThread(t); t.started.connect(w.run); w.done.connect(self._hash_done); w.failed.connect(self._hash_failed); w.done.connect(t.quit); w.failed.connect(t.quit); t.finished.connect(lambda:self._clear_thread(t,w)); self._thread=t; self._worker=w; t.start()
    def _hash_done(self,value):
        text=value or "Cancelled"; self.hash_item.setText(1,text); self._snapshot["Integrity"]=[("SHA-256",text)]
    def _hash_failed(self,msg):
        text=f"Error: {msg}"; self.hash_item.setText(1,text); self._snapshot["Integrity"]=[("SHA-256",text)]
    def _clear_thread(self,t,w):
        if self._thread is t: self._thread=None; self._worker=None; self.hash_btn.setEnabled(True)
        w.deleteLater(); t.deleteLater()
    def _cancel_hash(self):
        t=self._thread; w=getattr(self,"_worker",None)
        if not t: return
        if w:
            try: w.done.disconnect(self._hash_done)
            except (TypeError,RuntimeError): pass
            try: w.failed.disconnect(self._hash_failed)
            except (TypeError,RuntimeError): pass
        t.requestInterruption(); t.quit(); t.wait(3000)
        if self._thread is t: self._thread=None; self._worker=None; self.hash_btn.setEnabled(True)
    def shutdown(self): self._cancel_hash()

class TextDialog(QDialog):
    def __init__(self,title,text,parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setModal(False); self.resize(680,520); lay=QVBoxLayout(self); edit=QPlainTextEdit(); edit.setReadOnly(True); edit.setPlainText(text); lay.addWidget(edit); close=QPushButton("Close"); close.clicked.connect(self.hide); lay.addWidget(close,0,Qt.AlignmentFlag.AlignRight)



class KeyboardShortcutsDialog(QDialog):
    """Compact Crawlindo/Youlindo-style grouped shortcut reference."""
    def __init__(self,groups,parent=None):
        super().__init__(parent); self.setWindowTitle(f"Keyboard Shortcuts — {APP_NAME}"); self.setModal(False); self.setMinimumWidth(500)
        lay=QVBoxLayout(self); lay.setContentsMargins(18,16,18,14); lay.setSpacing(10)
        heading=QLabel("<b>Keyboard Shortcuts</b>",self); heading.setAlignment(Qt.AlignmentFlag.AlignCenter); heading.setTextFormat(Qt.TextFormat.RichText); lay.addWidget(heading)
        parts=["<table cellspacing='0' cellpadding='5' width='100%'>"]
        for group,rows in groups:
            parts.append(f"<tr><td colspan='2'><b>{html.escape(group)}</b></td></tr>")
            for label,sequence in rows:
                if isinstance(sequence,QKeySequence): text=sequence.toString(QKeySequence.SequenceFormat.NativeText)
                else: text=QKeySequence(str(sequence)).toString(QKeySequence.SequenceFormat.NativeText) if sequence else ""
                parts.append(f"<tr><td>{html.escape(label)}</td><td align='right'><code>{html.escape(text)}</code></td></tr>")
        parts.append("</table>")
        body=QLabel("".join(parts),self); body.setTextFormat(Qt.TextFormat.RichText); body.setWordWrap(False); body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); lay.addWidget(body,1)
        close=QPushButton("Close",self); close.clicked.connect(self.hide); lay.addWidget(close,0,Qt.AlignmentFlag.AlignRight)

class SelectionInspectorDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle(f"Selection Inspector — {APP_NAME}"); self.setModal(False); self.resize(620,460)
        lay=QVBoxLayout(self); self.title=QLabel("No selection",self); lay.addWidget(self.title)
        self.table=QTableWidget(0,2,self); self.table.setHorizontalHeaderLabels(["Interpretation","Value"]); self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); lay.addWidget(self.table,1)
        close=QPushButton("Close",self); close.clicked.connect(self.hide); lay.addWidget(close,0,Qt.AlignmentFlag.AlignRight)
    def set_values(self,offset_label:str,values:dict[str,str]):
        self.title.setText(f"Selection begins at {offset_label}")
        self.table.setRowCount(len(values))
        for row,(name,value) in enumerate(values.items()):
            self.table.setItem(row,0,QTableWidgetItem(name)); self.table.setItem(row,1,QTableWidgetItem(value))

class OffsetResultsDialog(QDialog):
    jumpRequested=pyqtSignal(int)
    def __init__(self,title,parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setModal(False); self.resize(700,520); self._rows=[]; self.offset_mode="hex"
        lay=QVBoxLayout(self); self.summary=QLabel(self); lay.addWidget(self.summary); self.filter=QLineEdit(self); self.filter.setPlaceholderText("Filter results…"); lay.addWidget(self.filter)
        self.list=QListWidget(self); lay.addWidget(self.list,1); row=QHBoxLayout(); row.addStretch(1); jump=QPushButton("Jump to Offset",self); close=QPushButton("Close",self); row.addWidget(jump); row.addWidget(close); lay.addLayout(row)
        self.filter.textChanged.connect(self._populate); self.list.itemDoubleClicked.connect(lambda _item:self._jump()); jump.clicked.connect(self._jump); close.clicked.connect(self.hide)
    def set_offset_mode(self,mode:str):
        if mode in ("hex","decimal","both"): self.offset_mode=mode; self._populate()
    def _format_offset(self,offset:int) -> str:
        if self.offset_mode=="decimal": return str(int(offset))
        if self.offset_mode=="both": return f"0x{int(offset):X} ({int(offset)})"
        return f"0x{int(offset):X}"
    def set_rows(self,rows:list[tuple[int,str]],summary:str=""):
        self._rows=list(rows); self.summary.setText(summary or f"{len(rows):,} result{'s' if len(rows)!=1 else ''}"); self._populate()
    def _populate(self,*_):
        q=self.filter.text().casefold(); self.list.clear()
        for offset,text in self._rows:
            label=f"{self._format_offset(offset)}  —  {text}"
            if q and q not in label.casefold(): continue
            item=QListWidgetItem(label); item.setData(Qt.ItemDataRole.UserRole,int(offset)); self.list.addItem(item)
        if self.list.count(): self.list.setCurrentRow(0)
    def _jump(self):
        item=self.list.currentItem()
        if item: self.jumpRequested.emit(int(item.data(Qt.ItemDataRole.UserRole)))

class BookmarkDialog(QDialog):
    jumpRequested=pyqtSignal(int); removeRequested=pyqtSignal(int); clearRequested=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle(f"Bookmarks — {APP_NAME}"); self.setModal(False); self.resize(540,430); self.offset_mode="hex"
        lay=QVBoxLayout(self); self.note=QLabel("Bookmarks are stored in a separate hashed database; source paths are not stored.",self); self.note.setWordWrap(True); lay.addWidget(self.note)
        self.list=QListWidget(self); lay.addWidget(self.list,1); row=QHBoxLayout(); self.jump=QPushButton("Jump",self); self.remove=QPushButton("Remove",self); self.clear=QPushButton("Clear File Bookmarks",self); close=QPushButton("Close",self); row.addWidget(self.jump); row.addWidget(self.remove); row.addWidget(self.clear); row.addStretch(1); row.addWidget(close); lay.addLayout(row)
        self.jump.clicked.connect(self._jump); self.remove.clicked.connect(self._remove); self.clear.clicked.connect(self.clearRequested); close.clicked.connect(self.hide); self.list.itemDoubleClicked.connect(lambda _item:self._jump())
    def set_offset_mode(self,mode:str):
        if mode in ("hex","decimal","both"): self.offset_mode=mode
    def _format_offset(self,offset:int) -> str:
        if self.offset_mode=="decimal": return str(int(offset))
        if self.offset_mode=="both": return f"0x{int(offset):X} ({int(offset)})"
        return f"0x{int(offset):X}"
    def set_bookmarks(self,bookmarks):
        self.list.clear()
        for b in bookmarks:
            label=self._format_offset(b.offset) + (f"  —  {b.label}" if b.label else "")
            item=QListWidgetItem(label); item.setData(Qt.ItemDataRole.UserRole,int(b.offset)); self.list.addItem(item)
        enabled=bool(bookmarks); self.jump.setEnabled(enabled); self.remove.setEnabled(enabled); self.clear.setEnabled(enabled)
    def _offset(self):
        item=self.list.currentItem(); return None if item is None else int(item.data(Qt.ItemDataRole.UserRole))
    def _jump(self):
        off=self._offset()
        if off is not None: self.jumpRequested.emit(off)
    def _remove(self):
        off=self._offset()
        if off is not None: self.removeRequested.emit(off)

class SimpleReportDialog(QDialog):
    def __init__(self,title,parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setModal(False); self.resize(650,470); lay=QVBoxLayout(self); self.edit=QPlainTextEdit(self); self.edit.setReadOnly(True); self.edit.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)); lay.addWidget(self.edit,1); close=QPushButton("Close",self); close.clicked.connect(self.hide); lay.addWidget(close,0,Qt.AlignmentFlag.AlignRight)
    def set_text(self,text:str): self.edit.setPlainText(text)


class ShortcutToolbarDialog(QDialog):
    """Choose QAction commands shown on the dedicated Shortcut Toolbar."""
    def __init__(self, catalog, selected, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add More Shortcuts — {APP_NAME}")
        self.setModal(True)
        self.resize(620, 520)
        selected=set(str(x) for x in selected)
        lay=QVBoxLayout(self)
        note=QLabel("Choose commands to show on the Shortcut Toolbar. The Main Toolbar remains dedicated to File / Edit / Inspect / View / Help menus, and the Find Bar stays independent below the viewer.", self)
        note.setWordWrap(True); lay.addWidget(note)
        self.search=QLineEdit(self); self.search.setPlaceholderText("Search commands…"); lay.addWidget(self.search)
        self.tree=QTreeWidget(self); self.tree.setColumnCount(2); self.tree.setHeaderLabels(["Command","Shortcut"])
        self.tree.header().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch); self.tree.header().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        for category, rows in catalog:
            parent_item=QTreeWidgetItem([str(category),""]); parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsSelectable); self.tree.addTopLevelItem(parent_item)
            for action_id, action in rows:
                shortcut=action.shortcut().toString(QKeySequence.SequenceFormat.NativeText) if not action.shortcut().isEmpty() else ""
                child=QTreeWidgetItem([action.text().replace("&",""), shortcut]); child.setData(0,Qt.ItemDataRole.UserRole,str(action_id)); child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0,Qt.CheckState.Checked if str(action_id) in selected else Qt.CheckState.Unchecked)
                if not action.icon().isNull(): child.setIcon(0,action.icon())
                parent_item.addChild(child)
            parent_item.setExpanded(True)
        lay.addWidget(self.tree,1)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok,self); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); lay.addWidget(buttons)
        self.search.textChanged.connect(self._filter)
    def _filter(self,text):
        q=str(text or "").casefold().strip()
        self.tree.setUpdatesEnabled(False)
        try:
            for i in range(self.tree.topLevelItemCount()):
                parent=self.tree.topLevelItem(i); any_visible=False
                for j in range(parent.childCount()):
                    item=parent.child(j)
                    visible=(not q) or q in (item.text(0)+" "+item.text(1)).casefold()
                    item.setHidden(not visible); any_visible = any_visible or visible
                parent.setHidden(bool(q) and not any_visible)
                if any_visible: parent.setExpanded(True)
        finally:
            self.tree.setUpdatesEnabled(True); self.tree.viewport().update()
    def selected_ids(self):
        result=[]
        for i in range(self.tree.topLevelItemCount()):
            parent=self.tree.topLevelItem(i)
            for j in range(parent.childCount()):
                item=parent.child(j)
                if item.checkState(0)==Qt.CheckState.Checked:
                    result.append(str(item.data(0,Qt.ItemDataRole.UserRole)))
        return result

class AboutDialog(QDialog):
    def __init__(self, icon_path: Path, preferences_path: Path, parent=None):
        super().__init__(parent); self.setWindowTitle(f"About — {APP_NAME}"); self.setModal(False); self.setMinimumWidth(390)
        if parent is not None: self.setWindowIcon(parent.windowIcon())
        layout=QVBoxLayout(self); layout.setContentsMargins(24,22,24,18); layout.setSpacing(10)
        if icon_path.is_file():
            logo=QLabel(self); logo.setAlignment(Qt.AlignmentFlag.AlignCenter); pix=QPixmap(str(icon_path))
            if not pix.isNull(): logo.setPixmap(pix.scaled(112,112,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)); layout.addWidget(logo)
        name=QLabel(f"<h2>{APP_NAME}</h2>",self); name.setTextFormat(Qt.TextFormat.RichText); name.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(name)
        version=QLabel(f"Version {APP_VERSION}",self); version.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(version)
        tagline=QLabel("<b>Friendly. Fast. Focused.</b>",self); tagline.setTextFormat(Qt.TextFormat.RichText); tagline.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(tagline)
        description=QLabel("A lightweight read-only binary, hexadecimal and metadata inspector with virtual Offset + Hex + ASCII viewing, byte/text search, signatures, inspection tools and bounded format-aware metadata.",self); description.setWordWrap(True); description.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(description)
        prefs=html.escape(str(preferences_path))
        details=QLabel(f"<a href='{GITHUB_URL}'>{GITHUB_URL}</a><br>Built on Python · PyQt6 · Qt<br><b>Preferences:</b> {prefs}<br><br>Copyright © 2026 Bruno Machado<br>[<a href='https://github.com/brunonlinespace/'>https://github.com/brunonlinespace/</a>]<br>Licensed under the GNU General Public License v3 or later.",self)
        details.setTextFormat(Qt.TextFormat.RichText); details.setAlignment(Qt.AlignmentFlag.AlignCenter); details.setOpenExternalLinks(True); details.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction); layout.addWidget(details)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok,self); ok=buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None: ok.setText("OK")
        buttons.accepted.connect(self.close); layout.addWidget(buttons)
