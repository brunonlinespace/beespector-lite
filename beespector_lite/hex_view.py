from __future__ import annotations
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QFontMetricsF, QPainter, QPen, QKeySequence
from PyQt6.QtWidgets import QAbstractScrollArea, QApplication, QMenu, QMessageBox
from .byte_source import ByteSource
from .formatting import as_hex, as_compact_hex, as_escaped, as_ascii
from .color_engine import byte_class, detected_string_mask


class HexView(QAbstractScrollArea):
    cursorChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal(int, int)
    MAX_COPY_BYTES = 16 * 1024 * 1024
    MAX_SCROLL = 1_500_000_000

    DARK = {
        "base": "#17191C", "header": "#24272B", "border": "#535960",
        "header_text": "#F4F6F8", "offset": "#AEB9C6", "normal": "#E7EBEF",
        "letter": "#E7EBEF", "number": "#F2C879", "punctuation": "#8ED6FF",
        "space": "#AEB9C6", "control": "#88939E", "nul": "#E78484",
        "non_ascii": "#C4A7E7", "string": "#A9DC76", "placeholder": "#9AA4AE",
        "selection": "#356A9F", "selected_text": "#FFFFFF",
    }
    LIGHT = {
        "base": "#FFFFFF", "header": "#ECEFF3", "border": "#AEB5BD",
        "header_text": "#1B2026", "offset": "#4D6478", "normal": "#20252B",
        "letter": "#20252B", "number": "#9A6700", "punctuation": "#006B8F",
        "space": "#687580", "control": "#6A7580", "nul": "#A32222",
        "non_ascii": "#7047A5", "string": "#2E6B2E", "placeholder": "#687580",
        "selection": "#B7D7F5", "selected_text": "#101418",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source: ByteSource | None = None
        self.bytes_per_row = 16
        self.show_ascii = True
        self.show_offset = True
        self.show_column_identifiers = True
        self._visible_cache_key: tuple[int,int,int] | None = None
        self._visible_cache_block = b""
        self._visible_cache_strings: tuple[bool,...] | bytes = ()
        self.canvas_scheme = "dark"
        self.text_colour_mode = "detected_strings"
        self.offset_mode = "hex"
        self.cursor_offset = 0
        self.anchor_offset = 0
        self._dragging = False
        self._font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self._font.setPointSize(11)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self.horizontalScrollBar().valueChanged.connect(self.viewport().update)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
        self._recompute_metrics()

    def display_font(self) -> QFont:
        return QFont(self._font)

    def set_display_font(self, font: QFont):
        candidate = QFont(font)
        size = candidate.pointSize()
        candidate.setPointSize(max(8, min(28, size if size > 0 else 11)))
        self._font = candidate
        self._recompute_metrics(); self.viewport().update()

    def set_font_size(self, points: int):
        font = QFont(self._font); font.setPointSize(max(8, min(28, int(points))))
        self.set_display_font(font)

    def font_size(self) -> int:
        return self._font.pointSize()

    def set_canvas_scheme(self, scheme: str):
        if scheme not in ("dark", "light"):
            return
        self.canvas_scheme = scheme; self.viewport().update()

    def set_text_colour_mode(self, mode: str):
        if mode not in ("off", "character_classes", "detected_strings"):
            return
        self.text_colour_mode = mode; self._invalidate_visible_cache(); self.viewport().update()

    def set_show_offset(self, show: bool):
        self.show_offset = bool(show); self._update_scrollbars(); self.viewport().update()

    def set_show_ascii(self, show: bool):
        self.show_ascii = bool(show); self._update_scrollbars(); self.viewport().update()

    def set_show_column_identifiers(self, show: bool):
        self.show_column_identifiers = bool(show); self._recompute_metrics(); self.viewport().update()

    def _logical_size(self) -> int:
        return self.source.size if self.source else 0

    def set_offset_mode(self, mode: str):
        if mode not in ("hex", "decimal", "both"):
            return
        self.offset_mode = mode; self._update_scrollbars(); self.viewport().update()

    def format_offset(self, offset: int) -> str:
        digits = self._offset_digits()
        if self.offset_mode == "decimal":
            return str(int(offset))
        if self.offset_mode == "both":
            return f"{offset:0{digits}X} ({offset})"
        return f"{offset:0{digits}X}"

    def offset_header(self) -> str:
        return {"hex":"OFFSET (HEX)","decimal":"OFFSET (DEC)","both":"OFFSET (HEX / DEC)"}.get(self.offset_mode,"OFFSET")

    def _offset_chars(self) -> int:
        header_min=len(self.offset_header())+2
        logical=self._logical_size()
        if not self.source:
            return max(header_min,18 if self.offset_mode == "both" else 12)
        if self.offset_mode == "decimal":
            return max(header_min,10,len(str(max(0,logical-1)))+2)
        if self.offset_mode == "both":
            return max(header_min,self._offset_digits()+len(str(max(0,logical-1)))+5)
        return max(header_min,self._offset_digits()+2)

    def _scheme(self):
        return self.DARK if self.canvas_scheme == "dark" else self.LIGHT

    def _recompute_metrics(self):
        fm = QFontMetricsF(self._font)
        self.char_w = max(7.0, fm.horizontalAdvance("0"))
        self.line_h = max(16.0, fm.height()+3)
        self.header_h = self.line_h + 8 + (self.line_h if self.show_column_identifiers else 0)
        self._update_scrollbars()

    def _invalidate_visible_cache(self):
        self._visible_cache_key = None; self._visible_cache_block = b""; self._visible_cache_strings = ()

    def set_source(self, source: ByteSource | None):
        self.source = source
        self._invalidate_visible_cache()
        self.cursor_offset = self.anchor_offset = 0
        self.verticalScrollBar().setValue(0); self.horizontalScrollBar().setValue(0)
        self._update_scrollbars(); self.viewport().update(); self._emit_selection()

    def set_bytes_per_row(self, count: int):
        count = int(count)
        if not (1 <= count <= 64):
            return
        self.bytes_per_row = count
        self._invalidate_visible_cache(); self._update_scrollbars(); self.ensure_cursor_visible(); self.viewport().update()

    def _total_rows(self) -> int:
        size=self._logical_size()
        if size == 0:
            return 0
        return (size + self.bytes_per_row - 1)//self.bytes_per_row

    def _visible_rows(self) -> int:
        return max(1, int((self.viewport().height()-self.header_h)//self.line_h)+1)

    def _row_to_scroll(self, row: int) -> int:
        total=max(1,self._total_rows()); maxv=self.verticalScrollBar().maximum()
        if total-1 <= maxv: return max(0,min(row,maxv))
        return int((max(0,min(row,total-1))/(total-1))*maxv)

    def _scroll_to_row(self, value: int) -> int:
        total=self._total_rows(); maxv=self.verticalScrollBar().maximum()
        if total <= 1: return 0
        if total-1 <= maxv: return min(value,total-1)
        return int((value/maxv)*(total-1)) if maxv else 0

    def _offset_digits(self) -> int:
        return 8 if self._logical_size() <= 0xFFFFFFFF else 16

    def _content_width(self) -> int:
        digits = self._offset_digits()
        offset_w=self._offset_chars()*self.char_w if self.show_offset else 0
        hex_w=(self.bytes_per_row*3+1)*self.char_w
        ascii_w=(self.bytes_per_row+2)*self.char_w if self.show_ascii else 0
        return int(24+offset_w+hex_w+ascii_w)

    def _update_scrollbars(self):
        if not hasattr(self,'char_w'): return
        rows=self._total_rows(); visible=self._visible_rows(); logical=max(0,rows-visible)
        vmax=min(logical,self.MAX_SCROLL); self.verticalScrollBar().setRange(0,vmax)
        if logical <= self.MAX_SCROLL: self.verticalScrollBar().setPageStep(max(1,visible))
        else: self.verticalScrollBar().setPageStep(max(1,int(visible/logical*self.MAX_SCROLL)))
        hmax=max(0,self._content_width()-self.viewport().width())
        self.horizontalScrollBar().setRange(0,hmax); self.horizontalScrollBar().setPageStep(max(1,self.viewport().width()))

    def resizeEvent(self,event):
        super().resizeEvent(event); self._update_scrollbars()

    def _layout(self):
        digits = self._offset_digits(); x0=12-self.horizontalScrollBar().value(); offset_x=x0
        hex_x=offset_x+(self._offset_chars()*self.char_w if self.show_offset else 0)
        ascii_x=hex_x+(self.bytes_per_row*3+1)*self.char_w
        return digits, offset_x, hex_x, ascii_x

    def _byte_colour_key(self, value: int, in_string: bool) -> str:
        if self.text_colour_mode == "off":
            return "normal"
        if self.text_colour_mode == "detected_strings" and in_string:
            return "string"
        kind = byte_class(value)
        if self.text_colour_mode == "detected_strings" and kind in ("letter", "number", "punctuation", "space"):
            return "normal"
        return kind


    def _visible_block(self, block_start: int, actual_available: int):
        source_id = id(self.source) if self.source is not None else 0
        key = (source_id, int(block_start), int(actual_available))
        if key != self._visible_cache_key:
            block = self.source.read(block_start, actual_available) if self.source and actual_available else b""
            strings = detected_string_mask(block, minimum=4) if self.text_colour_mode == "detected_strings" else (False,)*len(block)
            self._visible_cache_key = key; self._visible_cache_block = block; self._visible_cache_strings = strings
        return self._visible_cache_block, self._visible_cache_strings

    def paintEvent(self,event):
        p=QPainter(self.viewport()); rect=self.viewport().rect(); colors=self._scheme()
        p.fillRect(rect,QColor(colors["base"])); p.setFont(self._font)
        digits, ox, hx, ax=self._layout()
        p.fillRect(QRectF(0,0,rect.width(),self.header_h),QColor(colors["header"]))
        p.setPen(QColor(colors["header_text"]))
        title_h=self.line_h+8
        if self.show_offset:
            p.drawText(QRectF(ox,2,self._offset_chars()*self.char_w,title_h-4), Qt.AlignmentFlag.AlignVCenter, self.offset_header())
        p.drawText(QRectF(hx,2,20*self.char_w,title_h-4), Qt.AlignmentFlag.AlignVCenter, "HEX")
        if self.show_ascii:
            p.drawText(QRectF(ax,2,12*self.char_w,title_h-4), Qt.AlignmentFlag.AlignVCenter, "ASCII")
        if self.show_column_identifiers:
            ident_y=title_h-2
            for i in range(self.bytes_per_row):
                p.drawText(QRectF(hx+i*3*self.char_w,ident_y,2.2*self.char_w,self.line_h),Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignHCenter,f"{i:02X}")
        p.setPen(QPen(QColor(colors["border"])))
        p.drawLine(0,int(self.header_h-1),rect.width(),int(self.header_h-1))
        if not self.source:
            p.setPen(QColor(colors["placeholder"]))
            p.drawText(QRectF(20,self.header_h+20,rect.width()-40,60),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop,"Open a file to inspect its bytes.")
            return

        top=self._scroll_to_row(self.verticalScrollBar().value()); rows=self._visible_rows()
        block_start=top*self.bytes_per_row
        actual_available=max(0,min(rows*self.bytes_per_row,self.source.size-block_start))
        block,string_mask=self._visible_block(block_start,actual_available)
        logical_size=self._logical_size()
        sel0,sel1=self.selection_range()
        for vr in range(rows):
            row=top+vr; off=row*self.bytes_per_row
            if off >= logical_size: break
            local=vr*self.bytes_per_row
            y=self.header_h+vr*self.line_h
            if self.show_offset:
                p.setPen(QColor(colors["offset"]))
                p.drawText(QRectF(ox,y,self._offset_chars()*self.char_w,self.line_h),Qt.AlignmentFlag.AlignVCenter,self.format_offset(off))
            cells=min(self.bytes_per_row, logical_size-off)
            for i in range(cells):
                absolute=off+i; idx=absolute-block_start
                if not (0 <= idx < len(block)):
                    continue
                selected=sel0 <= absolute < sel1
                cell=QRectF(hx+i*3*self.char_w,y,2.2*self.char_w,self.line_h)
                acell=QRectF(ax+i*self.char_w,y,self.char_w,self.line_h)
                clip=event.rect(); hex_visible=cell.right() >= clip.left() and cell.left() <= clip.right(); ascii_visible=self.show_ascii and acell.right() >= clip.left() and acell.left() <= clip.right()
                if not hex_visible and not ascii_visible: continue
                b=block[idx]; color_key=self._byte_colour_key(b, bool(string_mask[idx]) if idx < len(string_mask) else False)
                if hex_visible:
                    if selected:
                        p.fillRect(cell,QColor(colors["selection"])); p.setPen(QColor(colors["selected_text"]))
                    else:
                        p.setPen(QColor(colors[color_key]))
                    p.drawText(cell,Qt.AlignmentFlag.AlignVCenter,f"{b:02X}")
                if ascii_visible:
                    if selected:
                        p.fillRect(acell,QColor(colors["selection"])); p.setPen(QColor(colors["selected_text"]))
                    else:
                        p.setPen(QColor(colors[color_key]))
                    p.drawText(acell,Qt.AlignmentFlag.AlignCenter,chr(b) if 32 <= b <= 126 else ".")

    def _offset_at(self,pos: QPoint) -> int | None:
        if not self.source or pos.y() < self.header_h: return None
        top=self._scroll_to_row(self.verticalScrollBar().value()); row=top+int((pos.y()-self.header_h)//self.line_h)
        _,_,hx,ax=self._layout(); x=pos.x(); col=None
        if hx <= x < hx+self.bytes_per_row*3*self.char_w: col=int((x-hx)//(3*self.char_w))
        elif self.show_ascii and ax <= x < ax+self.bytes_per_row*self.char_w: col=int((x-ax)//self.char_w)
        if col is None or not (0<=col<self.bytes_per_row): return None
        off=row*self.bytes_per_row+col
        return off if off < self.source.size else None

    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            off=self._offset_at(event.position().toPoint())
            if off is not None:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: self.cursor_offset=off
                else: self.anchor_offset=self.cursor_offset=off
                self._dragging=True; self._emit_selection(); self.viewport().update(); self.setFocus(); event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            off=self._offset_at(event.position().toPoint())
            if off is not None:
                self.cursor_offset=off; self._emit_selection(); self.viewport().update(); self.ensure_cursor_visible(); event.accept(); return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton: self._dragging=False
        super().mouseReleaseEvent(event)

    def selection_range(self) -> tuple[int,int]:
        if not self.source: return (0,0)
        a=max(0,min(self.anchor_offset,self.source.size-1 if self.source.size else 0)); c=max(0,min(self.cursor_offset,self.source.size-1 if self.source.size else 0))
        return (min(a,c), max(a,c)+1) if self.source.size else (0,0)

    def selected_bytes(self, max_bytes: int | None = None) -> bytes:
        if not self.source: return b""
        a,b=self.selection_range(); length=b-a
        if max_bytes is not None and length > max_bytes: raise ValueError(f"Selection is {length:,} bytes; copy is limited to {max_bytes:,} bytes.")
        return self.source.read(a,length)

    def select_all(self):
        if not self.source or self.source.size == 0: return
        self.anchor_offset = self.source.size - 1
        self.cursor_offset = 0
        self._emit_selection(); self.viewport().update()

    def set_selection(self, start: int, length: int):
        if not self.source or self.source.size==0: return
        start=max(0,min(start,self.source.size-1)); length=max(1,length)
        self.anchor_offset=start; self.cursor_offset=min(self.source.size-1,start+length-1)
        self.ensure_cursor_visible(); self._emit_selection(); self.viewport().update()

    def set_cursor(self, offset: int, extend=False):
        if not self.source or self.source.size==0: return
        offset=max(0,min(offset,self.source.size-1))
        if not extend: self.anchor_offset=offset
        self.cursor_offset=offset; self.ensure_cursor_visible(); self._emit_selection(); self.viewport().update()

    def _emit_selection(self):
        a,b=self.selection_range(); self.cursorChanged.emit(self.cursor_offset); self.selectionChanged.emit(a,b)

    def ensure_cursor_visible(self):
        if not self.source: return
        row=self.cursor_offset//self.bytes_per_row; top=self._scroll_to_row(self.verticalScrollBar().value()); vis=self._visible_rows()
        if row<top: self.verticalScrollBar().setValue(self._row_to_scroll(row))
        elif row>=top+vis: self.verticalScrollBar().setValue(self._row_to_scroll(max(0,row-vis+1)))

    def scroll_to_offset(self, offset: int):
        size=self._logical_size()
        if size <= 0: return
        offset=max(0,min(int(offset),size-1)); row=offset//self.bytes_per_row
        self.verticalScrollBar().setValue(self._row_to_scroll(row)); self.viewport().update()

    def keyPressEvent(self,event):
        if not self.source or self.source.size==0:
            super().keyPressEvent(event); return
        key=event.key(); mods=event.modifiers(); extend=bool(mods & Qt.KeyboardModifier.ShiftModifier); cur=self.cursor_offset
        if key==Qt.Key.Key_Left: cur-=1
        elif key==Qt.Key.Key_Right: cur+=1
        elif key==Qt.Key.Key_Up: cur-=self.bytes_per_row
        elif key==Qt.Key.Key_Down: cur+=self.bytes_per_row
        elif key==Qt.Key.Key_PageUp: cur-=self.bytes_per_row*self._visible_rows()
        elif key==Qt.Key.Key_PageDown: cur+=self.bytes_per_row*self._visible_rows()
        elif key==Qt.Key.Key_Home: cur=0 if mods & Qt.KeyboardModifier.ControlModifier else (cur//self.bytes_per_row)*self.bytes_per_row
        elif key==Qt.Key.Key_End: cur=self.source.size-1 if mods & Qt.KeyboardModifier.ControlModifier else min(self.source.size-1,(cur//self.bytes_per_row+1)*self.bytes_per_row-1)
        elif event.matches(QKeySequence.StandardKey.Copy): self.copy_selection("hex"); return
        else:
            super().keyPressEvent(event); return
        self.set_cursor(cur,extend=extend); event.accept()

    def copy_selection(self, kind="hex"):
        try: data=self.selected_bytes(self.MAX_COPY_BYTES)
        except ValueError as exc:
            QMessageBox.information(self,"Selection Too Large to Copy",str(exc)); return
        if not data: return
        funcs={"hex":as_hex,"compact":as_compact_hex,"escaped":as_escaped,"ascii":as_ascii}
        QApplication.clipboard().setText(funcs.get(kind,as_hex)(data))

    def clipboard_offset(self, offset: int) -> str:
        if self.offset_mode == "decimal": return str(int(offset))
        if self.offset_mode == "both": return f"0x{int(offset):X} ({int(offset)})"
        return f"0x{int(offset):X}"

    def copy_offset(self):
        if not self.source: return
        QApplication.clipboard().setText(self.clipboard_offset(self.cursor_offset))

    def copy_offset_and_bytes(self):
        if not self.source: return
        try: data=self.selected_bytes(self.MAX_COPY_BYTES)
        except ValueError as exc:
            QMessageBox.information(self,"Selection Too Large to Copy",str(exc)); return
        a,b=self.selection_range()
        QApplication.clipboard().setText(f"{self.clipboard_offset(a)}: {as_hex(data)}")

    def _context_menu(self,pos):
        m=QMenu(self)
        a=m.addAction("Copy Offset"); a.triggered.connect(self.copy_offset)
        a=m.addAction("Copy Offset + Bytes"); a.triggered.connect(self.copy_offset_and_bytes)
        m.addSeparator()
        for label,kind in (("Copy as Hex","hex"),("Copy as Compact Hex","compact"),("Copy as Escaped Bytes","escaped"),("Copy as ASCII","ascii")):
            a=m.addAction(label); start,end=self.selection_range(); a.setEnabled(end>start); a.triggered.connect(lambda _=False,k=kind:self.copy_selection(k))
        m.exec(self.viewport().mapToGlobal(pos))
